import logging

from os import environ as env


def log_level() -> int:
    """
    Logging level
    """
    return int(env.get('LOG_LEVEL', logging.DEBUG))


def postgres_host() -> str:
    """
    PostgreSQL host
    """
    return env.get('POSTGRES_HOST', 'localhost')


def postgres_port() -> int:
    """
    PostgreSQL port
    """
    return int(env.get('POSTGRES_PORT', 5432))


def postgres_username() -> str:
    """
    PostgreSQL username
    """
    return env.get('POSTGRES_USERNAME', 'postgres')


def postgres_password() -> str:
    """
    PostgreSQL password
    """
    return env.get('POSTGRES_PASSWORD', 'postgres')


def postgres_database() -> str:
    """
    PostgreSQL database
    """
    return env.get('POSTGRES_DATABASE', 'postgres')


def git_actor_name() -> str:
    """
    Git actor username
    """
    return env.get('GIT_ACTOR_NAME', 'ALTS')


def git_actor_email() -> str:
    """
    Git actor email
    """
    return env.get('GIT_ACTOR_EMAIL', 'metric@alts.local')


def git_commit_message() -> str:
    """
    Git commit message
    """
    return env.get('GIT_COMMIT_MESSAGE', 'Sending you an update!')


def git_private_repo_url() -> str:
    """
    Git private repositry URL with read and write permissions
    """
    return env.get('GIT_PRIVATE_REPO_URL')


def git_public_repo_url() -> str:
    """
    Git public repository URL with read and write permissions
    """
    return env.get('GIT_PUBLIC_REPO_URL')
