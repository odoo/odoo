# =============================================================================
# s3.tf — S3 buckets for attachments, backups, and logs
#
# Three buckets with:
# - SSE-KMS encryption (shared key with auto-rotation)
# - Versioning enabled (soft-delete recovery)
# - Block Public Access (all four flags)
# - Lifecycle transitions (Standard → IA → Glacier → expire)
# - Bucket Key Enabled (reduces KMS API costs by ~99%)
# =============================================================================

# ---------------------------------------------------------------------------
# KMS key for SSE-KMS encryption across all three buckets
# ---------------------------------------------------------------------------
resource "aws_kms_key" "s3" {
  description             = "SSE-KMS key for Odoo S3 buckets"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "${local.name_prefix}-s3-kms"
  }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# ---------------------------------------------------------------------------
# Attachments bucket — Odoo filestore (documents, invoices, images)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "attachments" {
  bucket = "${local.name_prefix}-attachments"

  tags = {
    Name    = "${local.name_prefix}-attachments"
    Purpose = "odoo-filestore"
  }
}

resource "aws_s3_bucket_versioning" "attachments" {
  bucket = aws_s3_bucket.attachments.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "attachments" {
  bucket = aws_s3_bucket.attachments.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  rule {
    id     = "archive-old-invoices"
    status = "Enabled"
    filter {
      prefix = ""
    }
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

# ---------------------------------------------------------------------------
# Backups bucket — nightly pg_dump
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "backups" {
  bucket = "${local.name_prefix}-backups"

  tags = {
    Name    = "${local.name_prefix}-backups"
    Purpose = "pg-dump-nightly"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "tier-and-expire-backups"
    status = "Enabled"
    filter {
      prefix = ""
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 3650
    }
  }
}

# ---------------------------------------------------------------------------
# Logs bucket — application logs and audit trail
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "logs" {
  bucket = "${local.name_prefix}-logs"

  tags = {
    Name    = "${local.name_prefix}-logs"
    Purpose = "app-logs-audit"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "tier-and-expire-logs"
    status = "Enabled"
    filter {
      prefix = ""
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 180
      storage_class = "GLACIER"
    }
    expiration {
      days = 730
    }
  }
}