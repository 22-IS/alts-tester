import logging
import subprocess
import tempfile
from pathlib import Path

import git
import sqlalchemy
import yaml

import config
import const

logging.basicConfig(level=config.log_level())


class RODict(dict):
    def __setitem__(self, key, value) -> None:
        raise RuntimeError('Modification is not supported')


class ALTSException(Exception):
    def __init__(self, message: str) -> None:
        self._message = message

    @property
    def message(self) -> str:
        return self._message


class App:
    def __init__(self) -> None:
        logging.debug('__init__()')

        try:
            self._prepare()
            self._perform()
        except Exception as e:
            logging.error('internal error, please contact administrator')
            logging.log(const.INTERNAL_LOG_LEVEL, e, exc_info=True)
        finally:
            self._cleanup()

    """
    BASIC
    """

    def _prepare(self) -> None:
        logging.debug('_prepare()')

        # Database engine
        self._engine = sqlalchemy.create_engine('postgresql://{}:{}@{}:{}/{}'.format(
            config.postgres_username(),
            config.postgres_password(),
            config.postgres_host(),
            config.postgres_port(),
            config.postgres_database()
        ))

        # Public repository
        self._public_repo_dir = tempfile.TemporaryDirectory()
        self._public_repo = git.Repo.clone_from(config.git_public_repo_url(), self._public_repo_dir.name)

        # Private repository
        self._private_repo_dir = tempfile.TemporaryDirectory()
        self._private_repo = git.Repo.clone_from(config.git_private_repo_url(), self._private_repo_dir.name)

        # Load data
        self._students = RODict(yaml.safe_load(
            (Path(self._private_repo_dir.name) / const.STUDENTS_FILE).read_text(encoding='utf-8')
        ) or {})

    def _perform(self) -> None:
        logging.debug('_perform()')

        try:
            # Try to read info file
            try:
                info = (
                    Path(self._public_repo_dir.name) / const.INFO_FILE
                ).read_text(encoding='utf-8').strip().split('\n')
                if len(info) < 2:
                    raise ALTSException('incorrect {} format'.format(const.INFO_FILE))
            except (FileExistsError, PermissionError, UnicodeDecodeError):
                raise ALTSException('failed to read {}'.format(const.INFO_FILE))

            # Check lab number
            lab_no = info[0].strip()
            self._log_internal('input', 'lab_no={}'.format(lab_no))
            if not (lab_no.isnumeric() or int(lab_no) > 0):
                raise ALTSException('incorrect lab number')
            lab_no = int(lab_no)

            # Check student
            code = info[1].strip()
            self._log_internal('input', 'code="{}"'.format(code))
            if code not in self._students.keys():
                raise ALTSException('student not found')

            # Display info about participant before test
            self._log_internal('about', 'name="{}" group="{}" lab_no={} variant_no={}'.format(
                self._students[code]['name'],
                self._students[code]['group'],
                lab_no,
                self._students[code]['variant']
            ))

            # Run test
            func_name = '_test_lab{}_var{}'.format(lab_no, self._students[code]['variant'])
            func = getattr(self, func_name, None)
            if not (func and callable(func)):
                raise ALTSException('no matching test')

            score = func()
            if type(score) is not int:
                score = 0
            assert 0 <= score <= 100
        except ALTSException as e:
            self._commit_message('Fail: {}'.format(e.message))
            self._log_internal('fail', 'message="{}"'.format(e.message))
            return

        # Commit result
        if score > 0:
            self._commit_score(
                code,
                self._students[code]['name'],
                self._students[code]['group'],
                lab_no,
                self._students[code]['variant'],
                score
            )
        self._commit_message(str(score))

        # Display results
        self._log_internal('result', 'code="{}" name="{}" group="{}" lab_no={} variant_no={} score={}'.format(
            code,
            self._students[code]['name'],
            self._students[code]['group'],
            lab_no,
            self._students[code]['variant'],
            score
        ))

    def _cleanup(self) -> None:
        logging.debug('_cleanup()')

        # Release public repo
        if getattr(self, '_public_repo', None) is not None:
            self._public_repo.close()

        # Release private repo
        if getattr(self, '_private_repo', None) is not None:
            self._private_repo.close()

        # Remove public repo temp dir
        if getattr(self, '_public_repo_dir', None) is not None:
            self._public_repo_dir.cleanup()

        # Remove private repo temp dir
        if getattr(self, '_private_repo_dir', None) is not None:
            self._private_repo_dir.cleanup()

    """
    UTILS
    """

    def _log_internal(self, stage: str, message: str) -> None:
        logging.debug('_log_internal()')
        logging.log(const.INTERNAL_LOG_LEVEL, '{} - {}'.format(stage, message))

    def _commit_message(self, message: str) -> None:
        logging.debug('_commit_message()')

        # Write message to result.txt
        with open(Path(self._public_repo_dir.name) / const.RESULT_FILE, 'w+', encoding='utf-8') as f:
            f.write(message + '\n')

        # Commit
        actor = git.Actor(config.git_actor_name(), config.git_actor_email())
        self._public_repo.index.add([const.RESULT_FILE])
        self._public_repo.index.commit(
            message=config.git_commit_message(),
            author=actor,
            committer=actor
        )
        self._public_repo.remote().push()

    def _commit_score(self, code: str, name: str, group: str, lab_no: int, variant_no: int, score: int) -> None:
        logging.debug('_commit_score()')

        # Save score to database
        with self._engine.connect() as con:
            con.execute(
                sqlalchemy.text(
                    'INSERT INTO alts_results ("code", "name", "group", "lab_no", "variant_no", "score") VALUES (:code, :name, :group, :lab_no, :variant_no, :score)'
                ),
                {
                    'code': code,
                    'name': name,
                    'group': group,
                    'lab_no': lab_no,
                    'variant_no': variant_no,
                    'score': score
                }
            )
            con.commit()

    def _run_script(self, content: str, args: str = '') -> tuple[int, str, str]:
        logging.debug('_run_script()')

        r = subprocess.run(
            args=[
                # Basic
                'docker', 'run',

                # Interactive mode
                '-i',

                # Remove after execution
                '--rm',

                # Limit privileges
                '--read-only',
                '--user', '1000:1000',
                '--cap-drop', 'all',
                '--security-opt', 'no-new-privileges',

                # Limit resources
                '--network', 'none',
                '--memory', '128m',
                '--memory-swap', '128m',
                '--cpus', '0.1',
                '--pids-limit', '32',

                # Select image
                'debian:12.13-slim',

                # Run script with timeout (5s - SIGTERM, 5s - SIGKILL, 10s - total)
                'timeout', '--foreground', '-k', '5s', '5s', '/bin/bash', '-s', '--', args
            ],
            input=content.replace('\r\n', '\n').encode('utf-8'),
            capture_output=True
        )

        return r.returncode, r.stdout.decode('utf-8').strip(), r.stderr.decode('utf-8').strip()

    """
    TESTS
    """

    # Example test (lab_no=1 variant_no=1)
    def _test_lab1_var1(self) -> int:
        logging.debug('_test_lab1_var1()')

        # Try to open script.sh
        try:
            script_content = (Path(self._public_repo_dir.name) / 'script.sh').read_text(encoding='utf-8')
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            self._log_internal('test', 'failed to open script.sh - {}'.format(repr(e)))
            return 0  # score = 0

        # Run scritpt (expected output is 'Hello World!')
        rcode, stdout, stderr = self._run_script(script_content)
        if not (rcode == 0 and stdout == 'Hello World!'):
            self._log_internal('test', 'wrong script.sh output - rcode={} stdout="{}" stderr="{}"'.format(
                rcode,
                stdout,
                stderr
            ))
            return 50  # score = 50

        # Success
        return 100  # score = 100


if __name__ == '__main__':
    App()
