"""Override ir.attachment to store files in S3 instead of the local filestore.

When ``ir_attachment.s3_bucket`` is set via ir.config_parameter,
``_file_read``, ``_file_write`` and ``_file_delete`` target the S3 bucket
using boto3 with IAM role credentials.  When the parameter is unset (local
dev), the default filestore behaviour is used unchanged.

The S3 object key mirrors the filestore path (``ab/<sha1hash>``) so an
existing filestore can be synced to S3 with ``aws s3 sync`` and the keys
match perfectly.
"""

import logging

import boto3
from botocore.exceptions import ClientError

from odoo import api, models

_logger = logging.getLogger(__name__)

# ir.config_parameter keys
S3_BUCKET_PARAM = "ir_attachment.s3_bucket"
S3_PREFIX_PARAM = "ir_attachment.s3_prefix"
S3_REGION_PARAM = "ir_attachment.s3_region"

# Default region when not configured
DEFAULT_REGION = "eu-west-1"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # ------------------------------------------------------------------
    # S3 configuration helpers
    # ------------------------------------------------------------------

    @api.model
    def _s3_bucket_name(self):
        """Return the S3 bucket name from ir.config_parameter, or ``False``."""
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(S3_BUCKET_PARAM)
            or False
        )

    @api.model
    def _s3_prefix(self):
        """Return an optional key prefix (e.g. ``'prod/filestore/'``)."""
        prefix = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(S3_PREFIX_PARAM)
            or ""
        )
        return prefix.rstrip("/") + "/" if prefix else ""

    @api.model
    def _s3_region(self):
        """Return the AWS region for S3 operations."""
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(S3_REGION_PARAM)
            or DEFAULT_REGION
        )

    @api.model
    def _s3_client(self):
        """Return a boto3 S3 client using the EC2 instance role.

        No access keys are configured — boto3 picks up credentials from
        the instance metadata service (IAM instance profile).
        """
        return boto3.client("s3", region_name=self._s3_region())

    @api.model
    def _s3_key(self, fname):
        """Convert a filestore-relative *fname* to a full S3 object key.

        Example: ``fname='ab/abcdef0123...'``
        → ``key='prefix/ab/abcdef0123...'``
        """
        return f"{self._s3_prefix()}{fname}"

    # ------------------------------------------------------------------
    # Override _file_read — read bytes from S3
    # ------------------------------------------------------------------

    @api.model
    def _file_read(self, fname, size=None):
        bucket = self._s3_bucket_name()
        if not bucket:
            return super()._file_read(fname, size)

        key = self._s3_key(fname)
        try:
            client = self._s3_client()
            kwargs = {"Bucket": bucket, "Key": key}
            if size:
                kwargs["Range"] = f"bytes=0-{size - 1}"
            response = client.get_object(**kwargs)
            return response["Body"].read()
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                _logger.warning("S3: key not found: s3://%s/%s", bucket, key)
                return b""
            _logger.exception("S3: error reading s3://%s/%s", bucket, key)
            return b""
        except Exception:
            _logger.exception("S3: error reading s3://%s/%s", bucket, key)
            return b""

    # ------------------------------------------------------------------
    # Override _file_write — upload bytes to S3
    # ------------------------------------------------------------------

    @api.model
    def _file_write(self, bin_value, checksum):
        bucket = self._s3_bucket_name()
        if not bucket:
            return super()._file_write(bin_value, checksum)

        # Build the same key layout Odoo uses: sha[:2] + '/' + sha
        fname = checksum[:2] + "/" + checksum
        key = self._s3_key(fname)

        try:
            client = self._s3_client()

            # Skip upload if an object with the same key and size already
            # exists (content-addressable deduplication).
            try:
                head = client.head_object(Bucket=bucket, Key=key)
                if head["ContentLength"] == len(bin_value):
                    _logger.debug(
                        "S3: skip upload (exists): s3://%s/%s", bucket, key,
                    )
                    return fname
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "404":
                    raise

            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=bin_value,
                ContentType="application/octet-stream",
                ServerSideEncryption="aws:kms",
            )
            _logger.debug(
                "S3: uploaded s3://%s/%s (%d bytes)",
                bucket, key, len(bin_value),
            )
            return fname
        except Exception:
            _logger.exception("S3: error writing s3://%s/%s", bucket, key)
            raise

    # ------------------------------------------------------------------
    # Override _file_delete — delete from S3 (no checklist GC needed)
    # ------------------------------------------------------------------

    @api.model
    def _file_delete(self, fname):
        bucket = self._s3_bucket_name()
        if not bucket:
            return super()._file_delete(fname)

        key = self._s3_key(fname)
        try:
            client = self._s3_client()
            client.delete_object(Bucket=bucket, Key=key)
            _logger.debug("S3: deleted s3://%s/%s", bucket, key)
        except Exception:
            _logger.exception("S3: error deleting s3://%s/%s", bucket, key)
