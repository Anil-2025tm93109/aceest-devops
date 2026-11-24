# ACEest Fitness – Kubernetes Deployment Guide

## Architecture

All resources are deployed in the `aceest` namespace.

| Component | Resource | Purpose |
|---|---|---|
| Main application | aceest-v2 Deployment | Main application |
| Main service | aceest-service | Main application access |
| Green | aceest-green Deployment | Green deployment |
| Canary | aceest-canary Deployment | Canary deployment |
| Shadow | aceest-shadow Deployment and Service | Internal shadow endpoint |
| A/B variants | aceest-a and aceest-b Deployments and Services | Independent variant endpoints |

A and B currently use the same container image. They are separate deployments, not an automatic traffic-splitting implementation.

The Shadow Service provides internal cluster access. It does not implement automatic traffic mirroring.

## Prerequisites

- Docker
- Minikube
- kubectl

## Start Minikube

`minikube start --driver=docker`

## Deploy resources

`kubectl apply -f k8s/base.yaml`

`kubectl apply -f k8s/green.yaml`

`kubectl apply -f k8s/canary.yaml`

`kubectl apply -f k8s/shadow.yaml`

`kubectl apply -f k8s/ab-variants.yaml`

## Verify resources

`kubectl get deployments,pods,services -n aceest`

## Access the application

`kubectl port-forward -n aceest svc/aceest-service 18080:5000`

In another terminal:

`curl http://localhost:18080/health`