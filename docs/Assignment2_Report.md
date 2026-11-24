# ACEest Fitness – DevOps Assignment 2 Report

## 1. Project Overview

The objective of this project was to implement a CI/CD workflow for the ACEest Fitness application using Git, Jenkins, Docker, Kubernetes, Pytest and SonarQube.

The application is a Flask-based fitness and gym management service. The implementation demonstrates source control, automated build and testing, container image creation, static code analysis, container registry publishing, and Kubernetes deployment strategies.

**Source repository:** https://github.com/Anil-2025tm93109/aceest-devops  
**Branch:** assignment-2  
**Docker Hub:** https://hub.docker.com/r/akumarnk/aceest-fitness

## 2. CI/CD Architecture and Implementation

The project uses the following workflow:

1. **Source control – Git and GitHub:** Application code, tests, Docker configuration, Jenkins pipeline, Kubernetes manifests and supporting scripts are maintained in a public GitHub repository. Work is maintained on the assignment-2 branch.
2. **Continuous integration – Jenkins:** Jenkins is configured with a Pipeline job connected to GitHub. SCM polling checks for repository changes and automatically triggers a pipeline build.
3. **Code quality – Ruff:** The pipeline performs Python linting to identify code-quality issues.
4. **Automated testing – Pytest:** Unit tests are executed as part of the pipeline. Tests are also run in a dedicated Docker test stage.
5. **Containerization – Docker:** A multi-stage Dockerfile separates the test environment from the runtime image. The runtime uses Gunicorn and a non-root application user. A health check is configured for the application.
6. **Static analysis – SonarQube:** Jenkins runs SonarQube analysis and evaluates the configured quality gate. The pipeline includes a quality-gate stage.
7. **Image registry – Docker Hub:** Version-tagged application images are published to the public repository `akumarnk/aceest-fitness`.
8. **Container orchestration – Kubernetes:** Minikube is used to deploy and validate the application and demonstrate deployment strategies.

## 3. Testing and Quality Results

Automated testing was performed using Pytest.

- **Unit tests:** 67 tests passed.
- **Code linting:** Ruff completed successfully with no reported lint errors.
- **Test coverage:** The local coverage run reported approximately 99% overall coverage.
- **SonarQube:** The New Code Quality Gate passed.
- **SonarQube coverage:** 90.9% on new code and 98.7% overall, as reported by the analysis.
- **Security and reliability findings:** The recorded analysis reported no bugs, vulnerabilities or security hotspots remaining unreviewed.

Jenkins build #6 completed successfully with checkout, build, lint, automated tests, runtime image build, smoke test, SonarQube analysis and quality-gate validation. SCM polling was also verified. A Docker Hub publishing stage has since been added to the Jenkinsfile; its successful execution is subject to a subsequent Jenkins run.

## 4. Containerization and Registry

The application is packaged using Docker. The Dockerfile uses separate test and runtime stages, installs application dependencies, runs the service using Gunicorn and configures a health check.

The following image tags were published to Docker Hub:

- `akumarnk/aceest-fitness:v2.0`
- `akumarnk/aceest-fitness:v2.1`

Both tags were verified using Docker manifest inspection. At the time of verification, both tags referenced the same image digest; therefore, they represent two published tags rather than two different image builds.

## 5. Kubernetes Deployment Strategies

The application was deployed and tested on a Minikube Kubernetes cluster in the `aceest` namespace. The following strategies were demonstrated:

- **Blue-Green deployment:** Blue and Green deployments were maintained. The service selector was switched between the deployments and application health was verified.
- **Canary deployment:** A canary deployment was introduced and its ready endpoints were verified alongside the existing application endpoints. The demonstration validates endpoint inclusion, not weighted traffic distribution.
- **Shadow deployment:** A controlled test script sent requests to both the production and shadow services. Both returned successful responses, while the production response remained the user-facing response. This is controlled request replay rather than transparent live traffic mirroring.
- **A/B testing:** A proxy routes requests based on the `X-Experiment` header to Variant A or Variant B. Both variants returned successful responses. The variants currently use the same application image.
- **Rolling update and rollback:** The deployment was updated from image tag v2.0 to v2.1. The rollout completed successfully, and a rollback restored v2.0.

The final cluster verification showed all seven deployments ready and all nine pods running and ready. The application health endpoint returned HTTP 200.

**Cluster access note:** The Minikube NodePort endpoint uses the VM's private network address. It is not a publicly accessible endpoint.

## 6. Challenges and Mitigations

- **Jenkins Docker access:** Jenkins initially required Docker group permissions to execute container operations. The Jenkins service account was added to the Docker group and the service restarted.
- **Pipeline and quality-gate integration:** SonarQube scanner configuration and the Jenkins webhook were configured to allow the pipeline to wait for and receive quality-gate results.
- **Kubernetes availability:** The Minikube cluster was restarted when the Kubernetes API became unavailable, after which deployment and health checks were repeated.
- **Deployment validation:** Each strategy was validated through Kubernetes deployment/service state, endpoint inspection, application responses or rollout status, with supporting evidence captured in the project.

## 7. Conclusion

The project demonstrates an integrated CI workflow using GitHub, Jenkins, automated tests, Docker and SonarQube, along with Docker Hub image publishing and Kubernetes deployment strategy exercises.

The recorded Jenkins build completed successfully, the SonarQube quality gate passed, the existing Docker Hub tags were verified, and the Kubernetes workloads passed the recorded readiness and application health checks. The newly added Docker Hub publishing stage requires a subsequent Jenkins run for execution verification.

The Kubernetes strategy demonstrations are proof-of-concept implementations. Weighted canary traffic, transparent production traffic mirroring, distinct A/B application variants, and a publicly reachable cluster endpoint would require additional configuration for a production-grade deployment.
