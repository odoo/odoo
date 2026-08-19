# =============================================================================
# routes.tf — Route tables and associations
#
# Public RT:  0.0.0.0/0 → IGW       (direct internet)
# App RT:     0.0.0.0/0 → NAT GW    (outbound only, no inbound)
# Data RT:    (no internet route)     — completely isolated
# =============================================================================

# ---------------------------------------------------------------------------
# Public route table — direct internet via IGW
# ---------------------------------------------------------------------------
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# App route table — outbound via NAT Gateway (no direct internet ingress)
# ---------------------------------------------------------------------------
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "${local.name_prefix}-app-rt"
  }
}

resource "aws_route_table_association" "app" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app.id
}

# ---------------------------------------------------------------------------
# Data route table — NO internet route (completely isolated)
#
# Instances in data subnets can only communicate with app subnets via
# security group rules. No 0.0.0.0/0 route exists — not even through NAT.
# This means RDS cannot be reached from the internet under any
# circumstance.
# ---------------------------------------------------------------------------
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id

  # Intentionally NO route block — data subnets are isolated

  tags = {
    Name = "${local.name_prefix}-data-rt"
  }
}

resource "aws_route_table_association" "data" {
  count          = length(var.azs)
  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}
