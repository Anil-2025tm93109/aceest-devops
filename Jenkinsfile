pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        TEST_IMAGE = "aceest-fitness:test-${BUILD_NUMBER}"
        RUN_IMAGE  = "aceest-fitness:jenkins-${BUILD_NUMBER}"
        CONTAINER  = "aceest-smoke-${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                // Pulls the latest code from the GitHub repository configured on the job
                checkout scm
            }
        }

        stage('Clean Build') {
            steps {
                // --no-cache forces a from-scratch build of the test image
                sh 'docker build --no-cache --target test -t "$TEST_IMAGE" .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm "$TEST_IMAGE" ruff check app.py tests'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'docker run --rm "$TEST_IMAGE"'
            }
        }

        stage('Build Runtime Image') {
            steps {
                sh 'docker build -t "$RUN_IMAGE" .'
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    docker run -d --name "$CONTAINER" "$RUN_IMAGE"
                    status=starting
                    for i in $(seq 1 30); do
                        status=$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER")
                        [ "$status" = "healthy" ] && break
                        sleep 2
                    done
                    if [ "$status" != "healthy" ]; then
                        docker logs "$CONTAINER"
                        echo "Container did not become healthy"
                        exit 1
                    fi
                    [ "$(docker exec "$CONTAINER" id -u)" != "0" ]
                    echo "Container is healthy and runs as a non-root user"
                '''
            }
        }
    }

    post {
        always {
            sh 'docker rm -f "$CONTAINER" || true'
            sh 'docker rmi -f "$TEST_IMAGE" || true'
        }
        success {
            echo '===== Jenkins build completed successfully ====='
        }
        failure {
            echo '===== Jenkins build FAILED ====='
        }
    }
}
