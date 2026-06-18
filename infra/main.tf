# INTERVIEW AMMUNITION: Official Terraform modules are preferred over raw resources because they encapsulate AWS best practices (such as secure default subnets routing, EKS security group configurations, IAM role alignments) into reusable, community-tested blueprints, reducing maintenance overhead and preventing custom configuration errors.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Fetch availability zones in the current region
data "aws_availability_zones" "available" {}

# VPC configuration using official AWS VPC module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "uptime-monitor-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# EKS Cluster configuration using official AWS EKS module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.30"

  cluster_endpoint_public_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    uptime_workers = {
      min_size     = 1
      max_size     = 1
      desired_size = 1

      instance_types = ["t3.micro"]
      capacity_type  = "ON_DEMAND"
    }
  }

  # Enable cluster creator admin permissions (IAM User running Terraform gets cluster access)
  enable_cluster_creator_admin_permissions = true
}

# Elastic Container Registry (ECR) for application image hosting
resource "aws_ecr_repository" "app" {
  name                 = "uptime-monitor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
