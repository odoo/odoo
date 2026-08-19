# =============================================================================
# security_groups.tf — Tiered security groups
#
# ALB SG:   80/443 from internet → forwards to App SG
# App SG:   8069 only from ALB SG, outbound 443 via NAT (pip/npm)
# Data SG:  5432 only from App SG (RDS access)
# SSM SG:   443 outbound only (SSM Session Manager, no SSH)
# =============================================================================

# ---------------------------------------------------------------------------
# ALB Security Group
# ---------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "Allow HTTP/HTTPS from internet, forward to Odoo app tier"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-alb-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP from internet"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "HTTPS from internet"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = var.odoo_port
  to_port                      = var.odoo_port
  ip_protocol                  = "tcp"
  description                  = "Forward to Odoo app tier"
}

# ---------------------------------------------------------------------------
# Application (Odoo) Security Group
# ---------------------------------------------------------------------------
resource "aws_security_group" "app" {
  name        = "${local.name_prefix}-app-sg"
  description = "Odoo app tier — inbound from ALB, outbound to internet via NAT"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-app-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = var.odoo_port
  to_port                      = var.odoo_port
  ip_protocol                  = "tcp"
  description                  = "Odoo HTTP from ALB only"
}

# Allow app tier to reach RDS on 5432
resource "aws_vpc_security_group_egress_rule" "app_to_data" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.data.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL to RDS"
}

# Allow outbound HTTPS (pip install, docker pull, apt-get via NAT)
resource "aws_vpc_security_group_egress_rule" "app_https_out" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "HTTPS outbound (NAT) for package managers"
}

# Allow outbound HTTP (apt repositories)
resource "aws_vpc_security_group_egress_rule" "app_http_out" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  description       = "HTTP outbound (NAT) for apt repositories"
}

# Allow outbound DNS
resource "aws_vpc_security_group_egress_rule" "app_dns" {
  security_group_id = aws_security_group.app.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
  description       = "DNS resolution"
}

# Allow outbound to Redis (sessions + LLM cache)
resource "aws_vpc_security_group_egress_rule" "app_to_redis" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.redis.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
  description                  = "Redis sessions + cache"
}

# ---------------------------------------------------------------------------
# Data (RDS) Security Group — inbound from app tier only
# ---------------------------------------------------------------------------
resource "aws_security_group" "data" {
  name                   = "${local.name_prefix}-data-sg"
  description            = "RDS PostgreSQL — inbound from app tier only"
  vpc_id                 = aws_vpc.main.id
  revoke_rules_on_delete = true

  tags = {
    Name = "${local.name_prefix}-data-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "data_from_app" {
  security_group_id            = aws_security_group.data.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  description                  = "PostgreSQL from app tier only"
}

# No egress rules — data subnet is isolated. Default VPC egress is removed
# by setting `revoke_rules_on_delete = true` on the security group.
# RDS does not need to initiate outbound connections.
