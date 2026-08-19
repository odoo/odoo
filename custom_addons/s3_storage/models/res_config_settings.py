"""S3 storage settings exposed in the Odoo Settings UI.

Three ir.config_parameter values control S3 storage:
- ir_attachment.s3_bucket — S3 bucket name (empty = local filestore)
- ir_attachment.s3_prefix — optional key prefix (e.g. 'prod/filestore/')
- ir_attachment.s3_region — AWS region (default: eu-west-1)
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    s3_bucket_name = fields.Char(
        string="S3 Bucket",
        config_parameter="ir_attachment.s3_bucket",
        help="AWS S3 bucket for attachment storage. Leave empty to use "
        "the local filestore (default for development).",
    )
    s3_prefix = fields.Char(
        string="S3 Key Prefix",
        config_parameter="ir_attachment.s3_prefix",
        help="Optional prefix for S3 object keys (e.g. 'prod/filestore'). "
        "All attachments will be stored under this prefix.",
    )
    s3_region = fields.Char(
        string="S3 Region",
        config_parameter="ir_attachment.s3_region",
        default="eu-west-1",
        help="AWS region of the S3 bucket.",
    )
