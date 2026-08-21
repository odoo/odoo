# =============================================================================
# elasticache.tf — Redis 7 cluster for Odoo sessions + LLM extraction cache
#
# - cache.t4g.medium (2 nodes: 1 primary + 1 replica)
# - Multi-AZ automatic failover
# - Transit encryption (TLS) + at-rest encryption (KMS)
# - AUTH token stored in Secrets Manager
# - Subnet group: data subnets only (no internet)
# - Security group: inbound 6379 from app SG only
# =============================================================================

# ---------------------------------------------------------------------------
# AUTH token for Redis (stored in Secrets Manager)
# ---------------------------------------------------------------------------
resource "random_password" "redis_auth" {
  length  = 32
  special = false # AUTH token: alphanumeric only per AWS spec
}

resource "aws_secretsmanager_secret" "redis_auth" {
  name                    = "${local.name_prefix}/elasticache/auth-token"
  description             = "AUTH token for ElastiCache Redis cluster"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-redis-secret"
  }
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id     = aws_secretsmanager_secret.redis_auth.id
  secret_string = random_password.redis_auth.result
}

# ---------------------------------------------------------------------------
# ElastiCache subnet group — data subnets only (no internet)
# ---------------------------------------------------------------------------
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnets"
  subnet_ids = aws_subnet.data[*].id

  description = "Data subnets for ElastiCache Redis"

  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# ---------------------------------------------------------------------------
# Security group — app tier only, port 6379
# ---------------------------------------------------------------------------
resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "ElastiCache Redis — inbound from app tier only"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-redis-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_app" {
  security_group_id            = aws_security_group.redis.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
  description                  = "Redis from app tier only"
}

resource "aws_vpc_security_group_egress_rule" "redis_default" {
  security_group_id = aws_security_group.redis.id
  cidr_ipv4         = aws_vpc.main.cidr_block
  from_port         = 6379
  to_port           = 6379
  ip_protocol       = "tcp"
  description       = "In-VPC Redis replication"
}

# ---------------------------------------------------------------------------
# Parameter group — tuned for session + cache workload
# ---------------------------------------------------------------------------
resource "aws_elasticache_parameter_group" "redis" {
  name        = "${local.name_prefix}-redis-params"
  family      = "redis7"
  description = "Parameters for Odoo session + LLM cache"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-ttl"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "" # No event notifications needed
  }

  tags = {
    Name = "${local.name_prefix}-redis-params"
  }
}

# ---------------------------------------------------------------------------
# Replication Group — Multi-AZ Redis 7.1
# ---------------------------------------------------------------------------
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.name_prefix}-redis"
  description          = "Redis 7 for Odoo sessions + LLM extraction cache"

  engine             = "redis"
  engine_version     = "7.1"
  node_type          = "cache.t4g.medium"
  num_cache_clusters = 2 # 1 primary + 1 replica for Multi-AZ failover

  parameter_group_name = aws_elasticache_parameter_group.redis.name

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  automatic_failover_enabled = true
  multi_az_enabled           = true

  # Maintenance window
  maintenance_window       = "tue:04:00-tue:05:00"
  snapshot_window          = "03:00-04:00"
  snapshot_retention_limit = 7

  port = 6379

  tags = {
    Name = "${local.name_prefix}-redis"
  }

  lifecycle {
    prevent_destroy = true
  }
}
