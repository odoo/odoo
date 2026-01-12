# Copyright 2023 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
from odoo import api, fields, models


class FsStorage(models.Model):
    _inherit = "fs.storage"

    # S3 specific fields
    aws_access_key_id = fields.Char(
        string="AWS Access Key ID",
        help="AWS Access Key ID for S3 authentication",
    )
    aws_secret_access_key = fields.Char(
        string="AWS Secret Access Key",
        help="AWS Secret Access Key for S3 authentication",
    )
    aws_region = fields.Char(
        string="AWS Region",
        default="us-east-1",
        help="AWS Region where the S3 bucket is located",
    )
    aws_bucket_name = fields.Char(
        string="AWS S3 Bucket Name",
        help="Name of the S3 bucket to use for storage",
    )
    aws_endpoint_url = fields.Char(
        string="AWS S3 Endpoint URL",
        help="Custom S3 endpoint URL (for S3-compatible services like LocalStack, MinIO)",
    )
    aws_use_ssl = fields.Boolean(
        string="Use HTTPS",
        default=True,
        help="Use HTTPS for S3 connections",
    )

    def _get_fs_options(self):
        """Override to add S3 configuration from fields."""
        self.ensure_one()
        
        if self.protocol == 's3':
            # Build S3 config from fields
            s3_config = {}
            
            if self.aws_access_key_id:
                s3_config['key'] = self.aws_access_key_id
            
            if self.aws_secret_access_key:
                s3_config['secret'] = self.aws_secret_access_key
            
            client_kwargs = {}
            if self.aws_region:
                client_kwargs['region_name'] = self.aws_region
            
            if self.aws_endpoint_url:
                client_kwargs['endpoint_url'] = self.aws_endpoint_url
            
            if client_kwargs:
                s3_config['client_kwargs'] = client_kwargs
            
            if not self.aws_use_ssl:
                s3_config['use_ssl'] = False
            
            return s3_config
        
        # For other protocols, use parent implementation
        return super()._get_fs_options()

    def get_directory_path(self):
        """Override to return bucket/path for S3."""
        self.ensure_one()
        if self.protocol == 's3' and self.aws_bucket_name:
            # For S3, directory_path needs to include bucket
            if self.directory_path:
                clean_path = self.directory_path.strip("/")
                if clean_path:
                    return f"{self.aws_bucket_name}/{clean_path}"
            return self.aws_bucket_name
        return super().get_directory_path()
