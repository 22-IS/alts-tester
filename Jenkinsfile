pipeline {
    agent any

    parameters {
        string(name: 'REPO_URL', defaultValue: '', description: 'Ссылка на репозиторий с правом чтения/записи')
    }

    environment {
        DOCKER_HOST = 'tcp://host.docker.internal:2375'
        GIT_PUBLIC_REPO_URL = "${params.REPO_URL}"
    }

    tools {
        'org.jenkinsci.plugins.docker.commons.tools.DockerTool' 'docker-cli'
    }

    stages {
        stage('Run task') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'alts-postgres-login',
                        usernameVariable: 'POSTGRES_USERNAME',
                        passwordVariable: 'POSTGRES_PASSWORD'
                    ),
                    string(
                        credentialsId: 'alts-git-private-repo-url',
                        variable: 'GIT_PRIVATE_REPO_URL'
                    )
                ]) {
                    sh '''
                        docker run \
                        --rm \
                        -e LOG_LEVEL=20 \
                        -e POSTGRES_HOST=127.0.0.1 \
                        -e POSTGRES_PORT=5432 \
                        -e POSTGRES_USERNAME=$POSTGRES_USERNAME \
                        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
                        -e POSTGRES_DATABASE=postgres \
                        -e GIT_PUBLIC_REPO_URL=$GIT_PUBLIC_REPO_URL \
                        -e GIT_PRIVATE_REPO_URL=$GIT_PRIVATE_REPO_URL \
                        alts-tester
                    '''
                }
            }
        }
    }
}
