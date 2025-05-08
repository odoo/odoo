# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from datetime import datetime, timezone, timedelta
from requests import Response
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError

from ..utils.cloud_storage_azure_utils import UserDelegationKey
from .. import uninstall_hook
from ..models.ir_attachment import CloudStorageAzureUserDelegationKeys, get_cloud_storage_azure_user_delegation_key


class TestCloudStorageAzureCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.DUMMY_AZURE_ACCOUNT_NAME = 'accountname'
        self.DUMMY_AZURE_TENANT_ID = 'tenantid'
        self.DUMMY_AZURE_CLIENT_ID = 'clientid'
        self.DUMMY_AZURE_CLIENT_SECRET = 'secret'
        self.container_name = 'container-name'
        self.env['ir.config_parameter'].set_param('cloud_storage_provider', 'azure')
        self.env['ir.config_parameter'].set_param('cloud_storage_azure_account_name', self.DUMMY_AZURE_ACCOUNT_NAME)
        self.env['ir.config_parameter'].set_param('cloud_storage_azure_tenant_id', self.DUMMY_AZURE_TENANT_ID)
        self.env['ir.config_parameter'].set_param('cloud_storage_azure_client_id', self.DUMMY_AZURE_CLIENT_ID)
        self.env['ir.config_parameter'].set_param('cloud_storage_azure_client_secret', self.DUMMY_AZURE_CLIENT_SECRET)
        self.env['ir.config_parameter'].set_param('cloud_storage_azure_container_name', self.container_name)

        self.DUMMY_USER_DELEGATION_KEY = UserDelegationKey()
        self.DUMMY_USER_DELEGATION_KEY.signed_oid = 'signed_oid'
        self.DUMMY_USER_DELEGATION_KEY.signed_tid = 'signed_tid'
        self.DUMMY_USER_DELEGATION_KEY.signed_start = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.DUMMY_USER_DELEGATION_KEY.signed_expiry = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.DUMMY_USER_DELEGATION_KEY.signed_service = 'b'
        self.DUMMY_USER_DELEGATION_KEY.signed_version = '2023-11-03'
        self.DUMMY_USER_DELEGATION_KEY.value = 'KEHG9q+1y6XGLHkDNv3pR2DhmbOfxeTf5KAJ5/ssNpU='

        self.DUMMY_USER_DELEGATION_KEY_XML = bytes(f"""<?xml version="1.0" encoding="utf-8"?>
        <UserDelegationKey>
            <SignedOid>{self.DUMMY_USER_DELEGATION_KEY.signed_oid}</SignedOid>
            <SignedTid>{self.DUMMY_USER_DELEGATION_KEY.signed_tid}</SignedTid>
            <SignedStart>{self.DUMMY_USER_DELEGATION_KEY.signed_start}</SignedStart>
            <SignedExpiry>{self.DUMMY_USER_DELEGATION_KEY.signed_expiry}</SignedExpiry>
            <SignedService>{self.DUMMY_USER_DELEGATION_KEY.signed_service}</SignedService>
            <SignedVersion>{self.DUMMY_USER_DELEGATION_KEY.signed_version}</SignedVersion>
            <Value>{self.DUMMY_USER_DELEGATION_KEY.value}</Value>
        </UserDelegationKey>""", 'utf-8')

        CloudStorageAzureUserDelegationKeys.clear()


class TestCloudStorageAzure(TestCloudStorageAzureCommon):
    def test_get_user_delegation_key_success(self):
        request_num = 0

        def post(url, **kwargs):
            nonlocal request_num
            request_num += 1
            response = Response()
            if url.startswith('https://login.microsoftonline.com'):
                response.status_code = 200
                response._content = bytes(json.dumps({'access_token': 'xxx'}), 'utf-8')
            if 'blob.core.windows.net' in url:
                response.status_code = 200
                response._content = self.DUMMY_USER_DELEGATION_KEY_XML
            return response

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post):
            get_cloud_storage_azure_user_delegation_key(self.env)
            self.assertEqual(request_num, 2, '2 requests to create new user_delegation_key')

            self.env.invalidate_all()
            get_cloud_storage_azure_user_delegation_key(self.env)
            self.assertEqual(request_num, 2, 'user_delegation_key should be reused if configuration is not changed')

            self.env.registry.clear_cache()
            get_cloud_storage_azure_user_delegation_key(self.env)
            self.assertEqual(request_num, 2, 'user_delegation_key should be reused if configuration is not changed')

            self.env['ir.config_parameter'].set_param('cloud_storage_azure_account_name', 'newaccountname2')
            self.env.registry.clear_cache()
            get_cloud_storage_azure_user_delegation_key(self.env)
            self.assertEqual(request_num, 4, '2 requests to create new user_delegation_key when the configuration is changed')

    def test_get_user_delegation_key_wrong_info(self):
        request_num = 0

        def post(url, **kwargs):
            nonlocal request_num
            request_num += 1
            response = Response()
            if url.startswith('https://login.microsoftonline.com'):
                response.status_code = 400  # bad request because of missing tenant_id and client_id are wrong
            if 'blob.core.windows.net' in url:
                response.status_code = 200
                response._content = self.DUMMY_USER_DELEGATION_KEY_XML
            return response

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post), \
                self.assertRaises(ValidationError):
            get_cloud_storage_azure_user_delegation_key(self.env)
        self.assertEqual(request_num, 1, '1 request to validate the validity of the client id and tenant id')

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post), \
                self.assertRaises(ValidationError):
            get_cloud_storage_azure_user_delegation_key(self.env)
        self.assertEqual(request_num, 2, '1 request to validate the validity of the client id and tenant id')

    def test_get_user_delegation_key_wrong_secret(self):
        request_num = 0

        def post(url, **kwargs):
            nonlocal request_num
            request_num += 1
            response = Response()
            if url.startswith('https://login.microsoftonline.com'):
                response.status_code = 401  # forbidden because the secret is wrong
            if 'blob.core.windows.net' in url:
                response.status_code = 200
                response._content = self.DUMMY_USER_DELEGATION_KEY_XML
            return response

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post), \
                self.assertRaises(ValidationError):
            get_cloud_storage_azure_user_delegation_key(self.env)
        self.assertEqual(request_num, 1, '1 request to validate the validity of the secret')

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post), \
                self.assertRaises(ValidationError):
            get_cloud_storage_azure_user_delegation_key(self.env)
        self.assertEqual(request_num, 1, '401 response should be cached in case the secret is expired')

    def test_get_user_delegation_key_wrong_account(self):
        def post(url, **kwargs):
            response = Response()
            if url.startswith('https://login.microsoftonline.com'):
                response.status_code = 200
                response._content = bytes(json.dumps({'access_token': 'xxx'}), 'utf-8')
            if 'blob.core.windows.net' in url:
                raise requests.exceptions.ConnectionError()  # account_name wrong: domain https://accountname.blob.core.windows.net doesn't exist
            return response

        with patch('odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post', post), \
                self.assertRaises(ValidationError):
            get_cloud_storage_azure_user_delegation_key(self.env)

    def test_generate_sas_url(self):
        with patch('odoo.addons.cloud_storage_azure.models.ir_attachment.get_cloud_storage_azure_user_delegation_key', return_value=self.DUMMY_USER_DELEGATION_KEY):
            # create test cloud attachment like route "/mail/attachment/upload"
            # with dummy binary
            attachment = self.env['ir.attachment'].create([{
                'name': 'test.txt',
                'mimetype': 'text/plain',
                'datas': b'',
            }])
            attachment._post_add_create(cloud_storage=True)
            attachment._generate_cloud_storage_upload_info()
            attachment._generate_cloud_storage_download_info()

    def test_azure_url_validation(self):
        file_name = 'test.txt'

        def mk_url(account_name='admin', container_name='odoo-container'):
            return f'https://{account_name}.blob.core.windows.net/{container_name}/{file_name}'

        attachment = self.env['ir.attachment'].create([{
            'name': file_name,
            'mimetype': 'text/plain',
            'datas': b'',
            'type': 'cloud_storage',
            'url': mk_url(self.DUMMY_AZURE_ACCOUNT_NAME, self.container_name),
        }])

        self.assertDictEqual(attachment._get_cloud_storage_azure_info(), {
            'account_name': self.DUMMY_AZURE_ACCOUNT_NAME,
            'container_name': self.container_name,
            'blob_name': file_name,
        })

        attachment.url = mk_url(account_name='admin4lyfe', container_name='1-c-o-n-t-a-i-n-e-r')
        self.assertDictEqual(attachment._get_cloud_storage_azure_info(), {
            'account_name': 'admin4lyfe',
            'container_name': '1-c-o-n-t-a-i-n-e-r',
            'blob_name': file_name,
        })

        # Invalid account names
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(account_name='LOWERCASEONLY')
            attachment._get_cloud_storage_azure_info()
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(account_name='no-hyphens')
            attachment._get_cloud_storage_azure_info()
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(account_name='no_underscores')
            attachment._get_cloud_storage_azure_info()

        # Invalid container names
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(container_name='LOWERCASEONLY')
            attachment._get_cloud_storage_azure_info()
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(container_name='-no-starting-hyphens')
            attachment._get_cloud_storage_azure_info()
        with self.assertRaises(ValidationError):
            attachment.url = mk_url(container_name='no_underscores')
            attachment._get_cloud_storage_azure_info()

    def test_uninstall_fail(self):
        with self.assertRaises(UserError, msg="Don't uninstall the module if there are Azure attachments in use"):
            attachment = self.env['ir.attachment'].create([{
                'name': 'test.txt',
                'mimetype': 'text/plain',
                'datas': b'',
            }])
            attachment._post_add_create(cloud_storage=True)
            attachment.flush_recordset()
            uninstall_hook(self.env)

    def test_uninstall_success(self):
        uninstall_hook(self.env)
        # make sure all sensitive data are removed
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_provider'))
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_azure_account_name'))
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_azure_tenant_id'))
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_azure_client_id'))
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_azure_client_secret'))
        self.assertFalse(self.env['ir.config_parameter'].get_param('cloud_storage_azure_container_name'))
