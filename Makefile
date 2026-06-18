# Makefile for managing uptime-monitor infrastructure and deployment
.PHONY: build push deploy destroy test clean

IMAGE_NAME ?= uptime-monitor
AWS_REGION ?= us-east-1

# Local python testing target
test:
	pytest -v app/

# Build Docker container locally
build:
	docker build -t $(IMAGE_NAME):latest ./app

# Login to ECR and push image
push:
	aws ecr-get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $$(cd infra && terraform output -raw ecr_repository_url)
	docker tag $(IMAGE_NAME):latest $$(cd infra && terraform output -raw ecr_repository_url):latest
	docker push $$(cd infra && terraform output -raw ecr_repository_url):latest

# Provision infrastructure and deploy manifests to EKS
deploy:
	cd infra && terraform init && terraform apply -auto-approve
	aws eks update-kubeconfig --name uptime-monitor-cluster --region $(AWS_REGION)
	# Inject ECR registry URL into Kubernetes deployment
	sed -i.bak "s|<ECR_URL>:latest|$$(cd infra && terraform output -raw ecr_repository_url):latest|g" k8s/deployment.yaml && rm -f k8s/deployment.yaml.bak
	kubectl apply -f k8s/
	kubectl rollout status deployment/uptime-monitor --timeout=120s

# Tear down EKS resources and destroy infrastructure
destroy:
	kubectl delete -f k8s/ --ignore-not-found=true
	cd infra && terraform destroy -auto-approve
