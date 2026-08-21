# =============================================================================
# subnets.tf — Public, Application (private), and Data (private) subnets
#
# Tiering rationale:
#   Public  (10.20.0.x / 10.20.1.x)  — ALB, NAT Gateway, SSM endpoint
#   App     (10.20.10.x / 10.20.11.x) — Odoo EC2, worker containers
#   Data    (10.20.20.x / 10.20.21.x) — RDS PostgreSQL (no internet)
# =============================================================================

# ---------------------------------------------------------------------------
# Public subnets
# ---------------------------------------------------------------------------
resource "aws_subnet" "public" {
  count                   = length(var.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-${var.azs[count.index]}"
    Tier = "public"
  }
}

# ---------------------------------------------------------------------------
# Application (private) subnets — Odoo lives here, no public IP
# ---------------------------------------------------------------------------
resource "aws_subnet" "app" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.app_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = {
    Name = "${local.name_prefix}-app-${var.azs[count.index]}"
    Tier = "app"
  }
}

# ---------------------------------------------------------------------------
# Data (private) subnets — RDS lives here, completely isolated
# ---------------------------------------------------------------------------
resource "aws_subnet" "data" {
  count             = length(var.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.data_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = {
    Name = "${local.name_prefix}-data-${var.azs[count.index]}"
    Tier = "data"
  }
}

# ---------------------------------------------------------------------------
# NAT Gateway — placed in first public subnet for private-subnet egress
# ---------------------------------------------------------------------------
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${local.name_prefix}-nat"
  }

  depends_on = [aws_internet_gateway.main]
}

# ---------------------------------------------------------------------------
# VPC Endpoint for S3 — keeps S3 traffic off the public internet
# ---------------------------------------------------------------------------
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = [
    aws_route_table.public.id,
    aws_route_table.app.id,
    aws_route_table.data.id,
  ]

  tags = {
    Name = "${local.name_prefix}-s3-endpoint"
  }
}
