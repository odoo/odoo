# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from datetime import datetime, timedelta, timezone

from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError


class ResConfigSettings(models.TransientModel):
    """
    Instructions:
    cloud_storage_azure_account_name, cloud_storage_azure_container_name:
        if changed and old container names are still in use, you should
        promise the current application registration has the permission
        to access all old containers.
    cloud_storage_azure_invalidate_user_delegation_key:
        invalidate the cached value for
        get_cloud_storage_azure_user_delegation_key
    """
    _inherit = 'res.config.settings'

    cloud_storage_provider = fields.Selection(selection_add=[('azure', 'Azure Cloud Storage')])

    cloud_storage_azure_account_name = fields.Char(
        string='Azure Account Name',
        config_parameter='cloud_storage_azure_account_name')
    cloud_storage_azure_container_name = fields.Char(
        string='Azure Container Name',
        config_parameter='cloud_storage_azure_container_name')
    # Application Registry Info
    cloud_storage_azure_tenant_id = fields.Char(
        string='Azure Tenant ID',
        config_parameter='cloud_storage_azure_tenant_id')
    cloud_storage_azure_client_id = fields.Char(
        string='Azure Client ID',
        config_parameter='cloud_storage_azure_client_id')
    cloud_storage_azure_client_secret = fields.Char(
        string='Azure Client Secret',
        config_parameter='cloud_storage_azure_client_secret')
    cloud_storage_azure_invalidate_user_delegation_key = fields.Boolean(
        string='Invalidate Cached Azure User Delegation Key',
    )

    def _get_cloud_storage_configuration(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider') != 'azure':
            return super()._get_cloud_storage_configuration
        configuration = {
            'container_name': ICP.get_param('cloud_storage_azure_container_name'),
            'account_name': ICP.get_param('cloud_storage_azure_account_name'),
            'tenant_id': ICP.get_param('cloud_storage_azure_tenant_id'),
            'client_id': ICP.get_param('cloud_storage_azure_client_id'),
            'client_secret': ICP.get_param('cloud_storage_azure_client_secret'),
        }
        return configuration if all(configuration.values()) else {}

    def _setup_cloud_storage_provider(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider') != 'azure':
            return super()._setup_cloud_storage_provider()
        blob_info = {
            'account_name': ICP.get_param('cloud_storage_azure_account_name'),
            'container_name': ICP.get_param('cloud_storage_azure_container_name'),
            # use different blob names in case the credentials are allowed to
            # overwrite an existing blob created by previous tests
            'blob_name': f'0/{datetime.now(timezone.utc)}.txt',
        }

        # check blob create permission
        upload_expiry = datetime.now(timezone.utc) + timedelta(seconds=self.env['ir.attachment']._cloud_storage_upload_url_time_to_expiry)
        upload_url = self.env['ir.attachment']._generate_cloud_storage_azure_sas_url(**blob_info, permission='c', expiry=upload_expiry)
        upload_response = requests.put(upload_url, data=b'', headers={'x-ms-blob-type': 'BlockBlob'}, timeout=5)
        if upload_response.status_code != 201:
            raise ValidationError(_('The connection string is not allowed to upload blobs to the container.\n%s', str(upload_response.text)))

        # check blob read permission
        download_expiry = datetime.now(timezone.utc) + timedelta(seconds=self.env['ir.attachment']._cloud_storage_download_url_time_to_expiry)
        download_url = self.env['ir.attachment']._generate_cloud_storage_azure_sas_url(**blob_info, permission='r', expiry=download_expiry)
        download_response = requests.get(download_url, timeout=5)
        if download_response.status_code != 200:
            raise ValidationError(_('The connection string is not allowed to download blobs from the container.\n%s', str(download_response.text)))

    def _check_cloud_storage_uninstallable(self):
        if self.env['ir.config_parameter'].get_param('cloud_storage_provider') != 'azure':
            return super()._check_cloud_storage_uninstallable()
        cr = self.env.cr
        cr.execute(
            """
                SELECT 1
                FROM ir_attachment
                WHERE type = 'cloud_storage'
                AND url LIKE 'https://%.blob.core.windows.net/%'
                LIMIT 1
            """,
        )
        if cr.fetchone():
            raise UserError(_('Some Azure attachments are in use, please migrate their cloud storages before disable this module'))

    def set_values(self):
        super().set_values()
        if self.cloud_storage_azure_invalidate_user_delegation_key:
            ICP = self.env['ir.config_parameter']
            old_seq = int(ICP.get_param('cloud_storage_azure_user_delegation_key_sequence', 0))
            ICP.set_param('cloud_storage_azure_user_delegation_key_sequence', old_seq + 1)
