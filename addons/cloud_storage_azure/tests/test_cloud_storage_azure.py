# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from datetime import datetime, timezone, timedelta
from requests import Response
from unittest.mock import patch
import base64

from odoo.addons.mail.tests.common import MockEmail
from odoo.tests.common import TransactionCase
from odoo.tests import Form
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
        self.container_name = 'container_name'
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


class TestCloudStorageAzure(TestCloudStorageAzureCommon, MockEmail):
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

    def test_mail_composer_cloud_storage_attachment(self):
        """Ensure cloud attachments are converted to links in outgoing emails."""

        partner = self.env["res.partner"].create({"name": "Cloud Test Partner", "email": "cloud@test.com"})
        cloud_attachment = self.env["ir.attachment"].create({
            "name": "cloud_attachment.txt",
            "type": "cloud_storage",
            "url": "https://storage.googleapis.com/fakebucket/cloud_attachment.txt",
            "res_model": "res.partner",
            "res_id": partner.id,
            "mimetype": "text/plain",
        })

        context = {
            'default_model': 'res.partner',
            'default_res_ids': [partner.id],
            'default_composition_mode': 'comment',
            'default_partner_ids': [partner.id],
        }
        composer = self.env['mail.compose.message'].with_context(context).create({
            'body': "<p>Hello</p>",
            'attachment_ids': [(4, cloud_attachment.id)],
        })
        composer_form = Form(composer)
        composer_form.body = "<p>Hello</p>"
        composer_form.attachment_ids.add(cloud_attachment)
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()
        sent_mail = next((m for m in self._mails if 'cloud_attachment.txt' in m['body']), None)
        self.assertIsNotNone(sent_mail)
        self.assertIn(self.env['ir.qweb']._render('mail.mail_attachment_links', {'attachments': cloud_attachment}), sent_mail['body'])

    def test_mail_composer_cloud_storage_attachment_multiple(self):
        """Ensure cloud attachments are converted to links in all outgoing emails and no duplicate links occur."""

        # Create multiple recipients
        partners = self.env["res.partner"].create([
            {"name": "Partner A", "email": "a@test.com"},
            {"name": "Partner B", "email": "b@test.com"},
        ])

        # Attachments: one cloud, one binary (below threshold), one binary (above threshold), one URL
        binary_small = self.env['ir.attachment'].create({
            'name': 'small.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'small content'),
            'res_model': 'res.partner',
            'res_id': partners[0].id,
            'mimetype': 'text/plain',
        })
        binary_large = self.env['ir.attachment'].create({
            'name': 'large.txt',
            'type': 'binary',
            'datas': base64.b64encode(b'x' * 10_000_000),  # ~10MB
            'res_model': 'res.partner',
            'res_id': partners[0].id,
            'mimetype': 'text/plain',
        })
        url_attachment = self.env['ir.attachment'].create({
            'name': 'external.txt',
            'type': 'url',
            'url': 'https://example.com/external.txt',
            'res_model': 'res.partner',
            'res_id': partners[0].id,
            'mimetype': 'text/plain',
        })
        cloud_attachment = self.env['ir.attachment'].create({
            'name': 'cloud_attachment.txt',
            'type': 'cloud_storage',
            'url': 'https://storage.googleapis.com/fakebucket/cloud_attachment.txt',
            'res_model': 'res.partner',
            'res_id': partners[0].id,
            'mimetype': 'text/plain',
        })

        context = {
            'default_model': 'res.partner',
            'default_res_ids': partners.ids,
            'default_composition_mode': 'comment',
            'default_partner_ids': partners.ids,
        }

        composer = self.env['mail.compose.message'].with_context(context).create({
            'body': "<p>Hello</p>",
            'attachment_ids': [
                (4, binary_small.id),
                (4, binary_large.id),
                (4, url_attachment.id),
                (4, cloud_attachment.id),
            ],
        })

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()

        cloud_link_html = self.env['ir.qweb']._render('mail.mail_attachment_links', {'attachments': cloud_attachment})

        matched_mails = [m for m in self._mails if all(p.email in m['email_to'] for p in partners)]
        self.assertTrue(matched_mails self._mail, "No mail sent to all expected partners.")

        for mail in matched_mails:
            self.assertIn(cloud_link_html, mail['body'])

        # Check cloud link appears only once per email body
        for mail in matched_mails:
            self.assertEqual(mail['body'].count(cloud_link_html), 1, "Duplicate cloud link found in email.")

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

