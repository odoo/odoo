# =============================================================================
# iam.tf — EC2 instance profile for S3 + Secrets Manager access
#
# Scoped to:
# - Attachments bucket: GetObject, PutObject, DeleteObject, ListBucket
# - Backups bucket: PutObject, ListBucket (write-only)
# - Logs bucket: PutObject (write-only)
# - KMS key: Decrypt, GenerateDataKey (for SSE-KMS operations)
# =============================================================================

# ---------------------------------------------------------------------------
# EC2 Assume Role
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_s3" {
  name               = "${local.name_prefix}-ec2-s3"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name = "${local.name_prefix}-ec2-s3-role"
  }
}

# ---------------------------------------------------------------------------
# S3 Access Policy
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "s3_access" {
  # Attachments: read + write + delete the filestore
  statement {
    sid    = "AttachmentsReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.attachments.arn,
      "${aws_s3_bucket.attachments.arn}/*",
    ]
  }

  # Backups: write-only (the timer pushes dumps)
  statement {
    sid    = "BackupsWrite"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.backups.arn,
      "${aws_s3_bucket.backups.arn}/*",
    ]
  }

  # Logs: write-only
  statement {
    sid    = "LogsWrite"
    effect = "Allow"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.logs.arn}/*",
    ]
  }

  # KMS: encrypt/decrypt for the shared S3 key
  statement {
    sid    = "KMSAccess"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
    resources = [
      aws_kms_key.s3.arn,
    ]
  }
}

resource "aws_iam_policy" "s3_access" {
  name        = "${local.name_prefix}-s3-access"
  description = "Scoped S3 access for Odoo filestore, backups, and logs"
  policy      = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy_attachment" "ec2_s3" {
  role       = aws_iam_role.ec2_s3.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# ---------------------------------------------------------------------------
# Instance Profile (attach to EC2)
# ---------------------------------------------------------------------------
resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2_s3.name
}

# ---------------------------------------------------------------------------
# Secrets Manager read policy (for Redis AUTH token, etc.)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "secrets_read" {
  statement {
    sid    = "ReadSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      aws_secretsmanager_secret.db_master.arn,
      aws_secretsmanager_secret.db_odoo_user.arn,
      aws_secretsmanager_secret.redis_auth.arn,
    ]
  }
}

resource "aws_iam_policy" "secrets_read" {
  name        = "${local.name_prefix}-secrets-read"
  description = "Read secrets for DB and Redis credentials"
  policy      = data.aws_iam_policy_document.secrets_read.json
}

resource "aws_iam_role_policy_attachment" "ec2_secrets" {
  role       = aws_iam_role.ec2_s3.name
  policy_arn = aws_iam_policy.secrets_read.arn
}
