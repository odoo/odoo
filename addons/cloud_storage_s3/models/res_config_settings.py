import contextlib

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import s3


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cloud_storage_provider = fields.Selection(selection_add=[("s3", "Amazon S3")])
    cloud_storage_s3_bucket_name = fields.Char(
        string="S3 Bucket Name",
        config_parameter=s3.PARAM_BUCKET,
    )
    cloud_storage_s3_region = fields.Char(
        string="AWS Region",
        config_parameter=s3.PARAM_REGION,
    )
    cloud_storage_s3_access_key_id = fields.Char(
        string="AWS Access Key ID",
        help="Stored encrypted in the credential vault, never as a system "
        "parameter. Leave both key fields empty to keep the stored keys.",
    )
    cloud_storage_s3_secret_access_key = fields.Char(string="AWS Secret Access Key")
    cloud_storage_s3_keys_set = fields.Boolean(
        string="IAM keys stored",
        readonly=True,
    )
    cloud_storage_s3_enabled = fields.Boolean(
        string="Use S3 in this environment",
        default=False,
        config_parameter="cloud_storage_s3_enabled",
        help="Master switch for THIS environment. When off, attachments are "
        "served from the local filestore and S3 is never contacted, even if a "
        "provider and credentials are configured (e.g. on a database restored "
        "from production). Production must turn this on explicitly.",
    )
    cloud_storage_s3_storage_mode = fields.Selection(
        selection=[
            ("s3_only", "S3 Only"),
            ("hybrid", "Hybrid (S3 + Local)"),
        ],
        string="S3 Storage Mode",
        default="s3_only",
        config_parameter="cloud_storage_s3_storage_mode",
        help="S3 Only: new attachments are uploaded straight to S3 from the "
        "browser and not kept locally. Hybrid: attachments are stored in the "
        "local filestore and mirrored to S3 by a scheduled job, keeping the "
        "local copy.",
    )

    def _is_s3_provider(self):
        return (
            self.env["ir.config_parameter"].get_param("cloud_storage_provider") == "s3"
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        res["cloud_storage_s3_keys_set"] = bool(s3.get_keys(self.env))
        return res

    def set_values(self):
        self._store_s3_keys()
        super().set_values()

    def _store_s3_keys(self):
        access_key_id = self.cloud_storage_s3_access_key_id
        secret_access_key = self.cloud_storage_s3_secret_access_key
        if bool(access_key_id) != bool(secret_access_key):
            raise UserError(
                self.env._(
                    "Provide both the Access Key ID and the Secret Access Key, "
                    "or leave both empty to keep the stored keys."
                )
            )
        if not access_key_id:
            return
        s3.store_keys(self.env, access_key_id, secret_access_key)
        self.write(
            {
                "cloud_storage_s3_access_key_id": False,
                "cloud_storage_s3_secret_access_key": False,
                "cloud_storage_s3_keys_set": True,
            }
        )

    def _setup_cloud_storage_provider(self):
        if not self._is_s3_provider():
            return super()._setup_cloud_storage_provider()
        icp = self.env["ir.config_parameter"]
        if icp.sudo().get_param("cloud_storage_s3_enabled") != "True":
            return None

        bucket = icp.get_param(s3.PARAM_BUCKET)
        client = s3.get_client(self.env)
        blob_name = "0/_setup_test.txt"

        try:
            client.put_object(Bucket=bucket, Key=blob_name, Body=b"setup_test")
        except Exception as e:
            raise ValidationError(
                self.env._(
                    "Cannot upload to the S3 bucket. Check your credentials and bucket permissions.\n%s",
                    str(e),
                )
            ) from e

        try:
            obj = client.get_object(Bucket=bucket, Key=blob_name)
            obj["Body"].read()
        except Exception as e:
            raise ValidationError(
                self.env._(
                    "Cannot download from the S3 bucket. Check your credentials and bucket permissions.\n%s",
                    str(e),
                )
            ) from e

        with contextlib.suppress(Exception):
            client.delete_object(Bucket=bucket, Key=blob_name)

        if icp.get_param("cloud_storage_s3_storage_mode") == "hybrid":
            return None

        cors_config = {
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET", "PUT"],
                    "AllowedHeaders": ["Content-Type"],
                    "MaxAgeSeconds": self.env[
                        "ir.attachment"
                    ]._cloud_storage_upload_url_time_to_expiry,
                }
            ],
        }
        try:
            client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)
        except Exception as e:
            raise ValidationError(
                self.env._(
                    "Cannot configure CORS on the S3 bucket. "
                    "Ensure the IAM user has s3:PutBucketCors permission.\n%s",
                    str(e),
                )
            ) from e

    def _get_cloud_storage_configuration(self):
        if not self._is_s3_provider():
            return super()._get_cloud_storage_configuration()
        return s3.get_config(self.env)

    def _check_cloud_storage_uninstallable(self):
        if not self._is_s3_provider():
            return super()._check_cloud_storage_uninstallable()
        s3_in_use = self.env["ir.attachment"].search_count(
            [
                ("type", "=", "cloud_storage"),
                ("url", "=like", "https://%.s3.%.amazonaws.com/%"),
            ],
            limit=1,
        )
        if s3_in_use:
            raise UserError(
                self.env._(
                    "Some S3 attachments are in use. "
                    "Please migrate cloud storage attachments before disabling the provider."
                )
            )
        return None
