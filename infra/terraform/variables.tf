# =============================================================================
# variables.tf — Input variables for the Odoo Invoice Agent infrastructure
# =============================================================================

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "odoo-invoice-agent"
}

variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-1"
}

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "azs" {
  description = "Availability Zones to deploy into (exactly 2)"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
}

# ---------------------------------------------------------------------------
# Subnet CIDRs
# ---------------------------------------------------------------------------
variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "app_subnet_cidrs" {
  description = "CIDR blocks for application (private) subnets (one per AZ)"
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "data_subnet_cidrs" {
  description = "CIDR blocks for data (private) subnets (one per AZ)"
  type        = list(string)
  default     = ["10.20.20.0/24", "10.20.21.0/24"]
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.4"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 50
}

variable "db_name" {
  description = "Name of the default database"
  type        = string
  default     = "odoo"
}

variable "db_master_username" {
  description = "Master username for RDS"
  type        = string
  default     = "odoo_admin"
}

variable "db_backup_retention_period" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "Mon:04:00-Mon:05:00"
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
variable "odoo_port" {
  description = "Port Odoo listens on"
  type        = number
  default     = 8069
}

variable "domain" {
  description = "Public domain name for the application"
  type        = string
  default     = ""
}
