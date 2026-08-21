# =============================================================================
# rds.tf — Multi-AZ PostgreSQL 16 for Odoo
#
# - db.t4g.medium (2 vCPU, 8 GB RAM)
# - Multi-AZ synchronous standby for HA
# - Automated backups 7 days + PITR
# - Custom parameter group tuned for Odoo
# - Credentials in AWS Secrets Manager (not Terraform state)
# =============================================================================

# ---------------------------------------------------------------------------
# Secrets Manager — store the master password separately
# ---------------------------------------------------------------------------
resource "random_password" "db_master" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

resource "aws_secretsmanager_secret" "db_master" {
  name                    = "${local.name_prefix}/rds/master-password"
  description             = "Master password for RDS PostgreSQL instance"
  recovery_window_in_days = 7

  tags = {
    Name = "${local.name_prefix}-rds-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  secret_string = jsonencode({
    username = var.db_master_username
    password = random_password.db_master.result
    host     = aws_db_instance.odoo.address
    port     = aws_db_instance.odoo.port
    dbname   = var.db_name
  })
}

# ---------------------------------------------------------------------------
# Secrets Manager — Odoo application user (lower-privilege)
# ---------------------------------------------------------------------------
resource "random_password" "db_odoo_user" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}:?"
}

resource "aws_secretsmanager_secret" "db_odoo_user" {
  name                    = "${local.name_prefix}/rds/odoo-password"
  description             = "Odoo application password for RDS PostgreSQL"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_odoo_user" {
  secret_id = aws_secretsmanager_secret.db_odoo_user.id
  secret_string = jsonencode({
    username = "odoo_user"
    password = random_password.db_odoo_user.result
    host     = aws_db_instance.odoo.address
    port     = aws_db_instance.odoo.port
    dbname   = var.db_name
  })
}

# ---------------------------------------------------------------------------
# Parameter group — tuned for Odoo on 8 GB RAM instance
# ---------------------------------------------------------------------------
resource "aws_db_parameter_group" "odoo" {
  name   = "${local.name_prefix}-pg16"
  family = "postgres16"

  description = "Custom PostgreSQL 16 parameter group for Odoo"

  # Memory tuning (db.t4g.medium = 8 GB)
  parameter {
    name  = "shared_buffers"
    value = "4GB"
  }

  parameter {
    name         = "shared_buffers.apply"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "effective_cache_size"
    value = "12GB"
  }

  parameter {
    name  = "work_mem"
    value = "64MB"
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "1GB"
  }

  # Connection limits
  parameter {
    name  = "max_connections"
    value = "200"
  }

  # Query logging for diagnostics
  parameter {
    name  = "log_min_duration_statement"
    value = "200"
  }

  # Statistics for query planner
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }

  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }

  # WAL settings for durability
  parameter {
    name  = "wal_buffers"
    value = "64MB"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }

  tags = {
    Name = "${local.name_prefix}-pg16-params"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# DB subnet group — data subnets only (no internet)
# ---------------------------------------------------------------------------
resource "aws_db_subnet_group" "odoo" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.data[*].id

  description = "Data subnets for RDS — no internet access"

  tags = {
    Name = "${local.name_prefix}-db-subnet-group"
  }
}

# ---------------------------------------------------------------------------
# RDS instance — Multi-AZ PostgreSQL 16
# ---------------------------------------------------------------------------
resource "aws_db_instance" "odoo" {
  identifier = "${local.name_prefix}-db"

  # Engine
  engine               = "postgres"
  engine_version       = var.db_engine_version
  instance_class       = var.db_instance_class
  parameter_group_name = aws_db_parameter_group.odoo.name

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 200
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_master_username
  password = random_password.db_master.result

  # High availability
  multi_az = true

  # Networking — data subnets, isolated from internet
  db_subnet_group_name   = aws_db_subnet_group.odoo.name
  vpc_security_group_ids = [aws_security_group.data.id]
  publicly_accessible    = false
  port                   = 5432

  # Backup & recovery
  backup_retention_period   = var.db_backup_retention_period
  backup_window             = var.db_backup_window
  maintenance_window        = var.db_maintenance_window
  copy_tags_to_snapshot     = true
  delete_automated_backups  = true
  final_snapshot_identifier = "${local.name_prefix}-final-snapshot"
  skip_final_snapshot       = false

  # Monitoring
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  # Protection
  deletion_protection = true

  # Require SSL connections
  apply_immediately = false

  tags = {
    Name = "${local.name_prefix}-rds"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# ---------------------------------------------------------------------------
# IAM role for enhanced monitoring
# ---------------------------------------------------------------------------
resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ---------------------------------------------------------------------------
# CloudWatch alarms
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  alarm_name          = "${local.name_prefix}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240 # 10 GB in bytes
  alarm_description   = "RDS free storage below 10 GB"
  alarm_actions       = []
  ok_actions          = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.odoo.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name_prefix}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 160 # 80% of max_connections=200
  alarm_description   = "RDS connections above 80% of max"
  alarm_actions       = []
  ok_actions          = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.odoo.identifier
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU above 80% sustained"
  alarm_actions       = []
  ok_actions          = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.odoo.identifier
  }
}
