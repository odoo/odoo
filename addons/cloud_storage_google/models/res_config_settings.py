# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import requests
from datetime import datetime, timezone

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
except ImportError:
    service_account = Request = None

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

from .ir_attachment import get_cloud_storage_google_credential


class ResConfigSettings(models.TransientModel):
    """
    Instructions:
    cloud_storage_google_bucket_name: if changed and the old bucket name
        are still in use, you should promise the current service account
        has the permission to access the old bucket.
    """
    _inherit = 'res.config.settings'

    cloud_storage_provider = fields.Selection(selection_add=[('google', 'Google Cloud Storage')])

    cloud_storage_google_bucket_name = fields.Char(
        string='Google Bucket Name',
        config_parameter='cloud_storage_google_bucket_name')
    # Google Service Account Key in JSON format
    cloud_storage_google_service_account_key = fields.Binary(
        string='Google Service Account Key', store=False
    )
    cloud_storage_google_account_info = fields.Char(
        string='Google Service Account Info',
        compute='_compute_cloud_storage_google_account_info',
        store=True,
        readonly=False,
        config_parameter='cloud_storage_google_account_info',
    )

    def get_values(self):
        res = super().get_values()
        if account_info := self.env['ir.config_parameter'].get_param('cloud_storage_google_account_info'):
            res['cloud_storage_google_service_account_key'] = base64.b64encode(account_info.encode())
        return res

    @api.onchange('cloud_storage_google_service_account_key')
    def _compute_cloud_storage_google_account_info(self):
        for setting in self:
            key = setting.with_context(bin_size=False).cloud_storage_google_service_account_key
            setting.cloud_storage_google_account_info = base64.b64decode(key) if key else False

    def _setup_cloud_storage_provider(self):
        ICP = self.env['ir.config_parameter']
        if ICP.get_param('cloud_storage_provider') != 'google':
            return super()._setup_cloud_storage_provider()
        # check bucket access
        bucket_name = ICP.get_param('cloud_storage_google_bucket_name')
        # use different blob names in case the credentials are allowed to
        # overwrite an existing blob created by previous tests
        blob_name = f'0/{datetime.now(timezone.utc)}.txt'

        IrAttachment = self.env['ir.attachment']
        # check blob create permission
        upload_url = IrAttachment._generate_cloud_storage_google_signed_url(bucket_name, blob_name, method='PUT', expiration=IrAttachment._cloud_storage_upload_url_time_to_expiry)
        upload_response = requests.put(upload_url, data=b'', timeout=5)
        if upload_response.status_code != 200:
            raise ValidationError(_('The account info is not allowed to upload blobs to the bucket.\n%s', str(upload_response.text)))

        # check blob read permission
        download_url = IrAttachment._generate_cloud_storage_google_signed_url(bucket_name, blob_name, method='GET', expiration=IrAttachment._cloud_storage_download_url_time_to_expiry)
        download_response = requests.get(download_url, timeout=5)
        if download_response.status_code != 200:
            raise ValidationError(_('The account info is not allowed to download blobs from the bucket.\n%s', str(upload_response.text)))

        # CORS management is not allowed in the Google Cloud console.
        # configure CORS on bucket to allow .pdf preview and direct upload
        cors = [{
            'origin': ['*'],
            'method': ['GET', 'PUT'],
            'responseHeader': ['Content-Type'],
            'maxAgeSeconds': IrAttachment._cloud_storage_download_url_time_to_expiry,
        }]
        credential = get_cloud_storage_google_credential(self.env).with_scopes(['https://www.googleapis.com/auth/devstorage.full_control'])
        credential.refresh(Request())
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}?fields=cors"
        headers = {
            'Authorization': f'Bearer {credential.token}',
            'Content-Type': 'application/json'
        }
        data = json.dumps({'cors': cors})
        patch_response = requests.patch(url, data=data, headers=headers, timeout=5)
        if patch_response.status_code != 200:
            raise ValidationError(_("The account info is not allowed to set the bucket's CORS.\n%s", str(patch_response.text)))

    def _get_cloud_storage_configuration(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider') != 'google':
            return super()._get_cloud_storage_configuration()
        configuration = {
            'bucket_name': ICP.get_param('cloud_storage_google_bucket_name'),
            'account_info': ICP.get_param('cloud_storage_google_account_info'),
        }
        return configuration if all(configuration.values()) else {}

    def _check_cloud_storage_uninstallable(self):
        if self.env['ir.config_parameter'].get_param('cloud_storage_provider') != 'google':
            return super()._check_cloud_storage_uninstallable()
        cr = self.env.cr
        cr.execute(
            """
                SELECT type
                FROM ir_attachment
                WHERE type = 'cloud_storage'
                AND url LIKE 'https://storage.googleapis.com/%'
                LIMIT 1
            """
        )
        if cr.fetchone():
            raise UserError(_('Some Google attachments are in use, please migrate cloud storages before disable the provider'))
