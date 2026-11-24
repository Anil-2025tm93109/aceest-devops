
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
                checkout scm
            }
        }

        stage('Clean Build') {
            steps {
                sh 'docker build --no-cache --target test -t "$TEST_IMAGE" .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm "$TEST_IMAGE" ruff check app.py tests'
            }
        }

        stage('Unit Tests and Coverage') {
            steps {
                sh '''
                    docker run --rm \
                      -v "$WORKSPACE:/workspace" \
                      -w /app \
                      "$TEST_IMAGE" \
                      python -m pytest \
                      --cov=app \
                      --cov=scripts.ab_proxy \
                      --cov-report=term-missing \
                      --cov-report=xml:/workspace/coverage.xml
                '''
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

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '/usr/local/bin/sonar-scanner'
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        set +x
                        IMAGE="akumarnk/aceest-fitness:build-$BUILD_NUMBER"
                        echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        docker tag "$RUN_IMAGE" "$IMAGE"
                        docker push "$IMAGE"
                        docker logout
                        echo "Published $IMAGE"
                    '''
                }
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
