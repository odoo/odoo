# =============================================================================
# outputs.tf — Useful values for downstream scripts, documentation, and addons
# =============================================================================

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

# ---------------------------------------------------------------------------
# Subnets
# ---------------------------------------------------------------------------
output "public_subnet_ids" {
  description = "Public subnet IDs (ALB, NAT)"
  value       = aws_subnet.public[*].id
}

output "app_subnet_ids" {
  description = "Application subnet IDs (Odoo EC2)"
  value       = aws_subnet.app[*].id
}

output "data_subnet_ids" {
  description = "Data subnet IDs (RDS, ElastiCache)"
  value       = aws_subnet.data[*].id
}

# ---------------------------------------------------------------------------
# NAT Gateway
# ---------------------------------------------------------------------------
output "nat_gateway_ip" {
  description = "Elastic IP of the NAT Gateway"
  value       = aws_eip.nat.public_ip
}

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------
output "rds_endpoint" {
  description = "RDS instance endpoint (hostname:port)"
  value       = aws_db_instance.odoo.endpoint
}

output "rds_hostname" {
  description = "RDS instance hostname"
  value       = aws_db_instance.odoo.address
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.odoo.port
}

output "rds_multi_az" {
  description = "Whether RDS is Multi-AZ"
  value       = aws_db_instance.odoo.multi_az
}

# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------
output "db_master_secret_arn" {
  description = "ARN of the master password secret"
  value       = aws_secretsmanager_secret.db_master.arn
}

output "db_odoo_user_secret_arn" {
  description = "ARN of the Odoo user password secret"
  value       = aws_secretsmanager_secret.db_odoo_user.arn
}

# ---------------------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------------------
output "alb_sg_id" {
  description = "Security Group ID for the ALB"
  value       = aws_security_group.alb.id
}

output "app_sg_id" {
  description = "Security Group ID for the application tier"
  value       = aws_security_group.app.id
}

output "data_sg_id" {
  description = "Security Group ID for the data tier"
  value       = aws_security_group.data.id
}

# ---------------------------------------------------------------------------
# S3 Buckets
# ---------------------------------------------------------------------------
output "s3_attachments_bucket" {
  description = "S3 bucket name for Odoo filestore attachments"
  value       = aws_s3_bucket.attachments.id
}

output "s3_backups_bucket" {
  description = "S3 bucket name for nightly pg_dump backups"
  value       = aws_s3_bucket.backups.id
}

output "s3_logs_bucket" {
  description = "S3 bucket name for application logs"
  value       = aws_s3_bucket.logs.id
}

output "s3_kms_key_arn" {
  description = "ARN of the KMS key for S3 SSE-KMS"
  value       = aws_kms_key.s3.arn
}

# ---------------------------------------------------------------------------
# EC2 Instance Profile
# ---------------------------------------------------------------------------
output "ec2_instance_profile_name" {
  description = "IAM instance profile to attach to EC2"
  value       = aws_iam_instance_profile.ec2.name
}

output "ec2_instance_profile_arn" {
  description = "ARN of the IAM instance profile"
  value       = aws_iam_instance_profile.ec2.arn
}

# ---------------------------------------------------------------------------
# ElastiCache Redis
# ---------------------------------------------------------------------------
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint (read replicas)"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = 6379
}

output "redis_secret_arn" {
  description = "ARN of the Redis AUTH token secret"
  value       = aws_secretsmanager_secret.redis_auth.arn
}

output "redis_security_group_id" {
  description = "Security Group ID for ElastiCache Redis"
  value       = aws_security_group.redis.id
}
