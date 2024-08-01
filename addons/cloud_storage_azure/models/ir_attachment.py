# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, quote

from odoo import models
from odoo.exceptions import ValidationError

from ..utils.cloud_storage_azure_utils import generate_blob_sas, get_user_delegation_key, ClientAuthenticationError

CloudStorageAzureUserDelegationKeys = {}  # {db_name: (config, user_delegation_key or exception)}


def get_cloud_storage_azure_user_delegation_key(env):
    """
    Generate a UserDelegationKey used for generating SAS tokens.

    The cached UserDelegationKey is refreshed every 6 days. If the account
    information expires, a ClientAuthenticationError will also be cached to
    prevent the server from repeatedly sending requests to the cloud
    storage provider to get the user delegation key. Note that the cached
    values are not invalidated when the ORM cache is invalidated. To
    invalidate these cached values, you must update the cloud storage
    configuration or the cloud_storage_azure_user_delegation_key_sequence.

    :return: A valid and unexpired UserDelegationKey which is compatible
            with azure.storage.blob.UserDelegationKey
    """
    cached_config, cached_user_delegation_key = CloudStorageAzureUserDelegationKeys.get(env.registry.db_name, (None, None))
    db_config = env['res.config.settings']._get_cloud_storage_configuration()
    db_config.pop('container_name')
    ICP = env['ir.config_parameter'].sudo()
    db_config['sequence'] = int(ICP.get_param('cloud_storage_azure_user_delegation_key_sequence', 0))
    if db_config == cached_config:
        if isinstance(cached_user_delegation_key, Exception):
            raise cached_user_delegation_key
        if cached_user_delegation_key:
            expiry = datetime.strptime(cached_user_delegation_key.signed_expiry, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if expiry > datetime.now(timezone.utc) + timedelta(days=1):
                return cached_user_delegation_key
    key_start_time = datetime.now(timezone.utc)
    key_expiry_time = key_start_time + timedelta(days=7)
    try:
        user_delegation_key = get_user_delegation_key(
            tenant_id=db_config['tenant_id'],
            client_id=db_config['client_id'],
            client_secret=db_config['client_secret'],
            account_name=db_config['account_name'],
            key_start_time=key_start_time,
            key_expiry_time=key_expiry_time,
        )
        CloudStorageAzureUserDelegationKeys[env.registry.db_name] = (db_config, user_delegation_key)
    except ClientAuthenticationError as e:
        ve = ValidationError(e)
        CloudStorageAzureUserDelegationKeys[env.registry.db_name] = (db_config, ve)
        raise ve
    return user_delegation_key


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _cloud_storage_azure_url_pattern = re.compile(r'https://(?P<account_name>[\w]+).blob.core.windows.net/(?P<container_name>[\w]+)/(?P<blob_name>[^?]+)')

    def _get_cloud_storage_azure_info(self):
        match = self._cloud_storage_azure_url_pattern.match(self.url)
        if not match:
            raise ValidationError('%s is not a valid Azure Blob Storage URL.', self.url)
        return {
            'account_name': match['account_name'],
            'container_name': match['container_name'],
            'blob_name': unquote(match['blob_name']),
        }

    def _generate_cloud_storage_azure_url(self, blob_name):
        ICP = self.env['ir.config_parameter'].sudo()
        account_name = ICP.get_param('cloud_storage_azure_account_name')
        container_name = ICP.get_param('cloud_storage_azure_container_name')
        return f"https://{account_name}.blob.core.windows.net/{container_name}/{quote(blob_name)}"

    def _generate_cloud_storage_azure_sas_url(self, **kwargs):
        token = generate_blob_sas(user_delegation_key=get_cloud_storage_azure_user_delegation_key(self.env), **kwargs)
        return f"{self._generate_cloud_storage_azure_url(kwargs['blob_name'])}?{token}"

    # OVERRIDES
    def _generate_cloud_storage_url(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 'azure':
            return super()._generate_cloud_storage_url()
        blob_name = self._generate_cloud_storage_blob_name()
        return self._generate_cloud_storage_azure_url(blob_name)

    def _generate_cloud_storage_download_info(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 'azure':
            return super()._generate_cloud_storage_download_info()
        info = self._get_cloud_storage_azure_info()
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self._cloud_storage_download_url_time_to_expiry)
        return {
            'url': self._generate_cloud_storage_azure_sas_url(**info, permission='r', expiry=expiry, cache_control=f'private, max-age={self._cloud_storage_download_url_time_to_expiry}'),
            'time_to_expiry': self._cloud_storage_download_url_time_to_expiry,
        }

    def _generate_cloud_storage_upload_info(self):
        if self.env['ir.config_parameter'].sudo().get_param('cloud_storage_provider') != 'azure':
            return super()._generate_cloud_storage_upload_info()
        info = self._get_cloud_storage_azure_info()
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self._cloud_storage_upload_url_time_to_expiry)
        url = self._generate_cloud_storage_azure_sas_url(**info, permission='c', expiry=expiry)
        return {
            'url': url,
            'method': 'PUT',
            'headers': {
                'x-ms-blob-type': 'BlockBlob',
            },
            'response_status': 201,
        }
