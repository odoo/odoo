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

    def test_cloud_storage_attachments(self):
        """Cloud attachments should be converted to links in outgoing emails."""

        thread_model = self.env["res.partner"].create({"name": "Cloud Test Partner", "email": "cloud@test.com"})
        cloud_attachment = self.env["ir.attachment"].create({
                "name": "cloud_attachment.txt",
                "type": "cloud_storage",
                "url": "https://storage.googleapis.com/fakebucket/cloud_attachment.txt",
                "res_model": "res.partner",
                "res_id": thread_model.id,
                "mimetype": "text/plain",
        })

        # A cloud attachment sent to a multiple partners -> attachment should be included as link in each
        partners = self.env["res.partner"].create([
                {"name": "Partner A", "email": "a@test.com"},
                {"name": "Partner B", "email": "b@test.com"},
        ])
        composer_form = Form(self.env["mail.compose.message"].with_context(
            default_model="res.partner",
            default_res_ids=thread_model.ids,
            default_composition_mode="comment",
            default_force_send=True,
            default_partner_ids=partners.ids,
        ))
        composer_form.attachment_ids.add(cloud_attachment)
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()
        self.assertEqual(len(self._mails), 2, "Two emails should be sent.")

        for body, attachment in zip([m["body"] for m in self._mails], self._new_mails.attachment_ids):
            large_attachment_link = str(self.env["ir.qweb"]._render("mail.mail_attachment_links", {"attachments": attachment}))
            self.assertEqual(body.count(large_attachment_link), 1,
                    "Sending mail with cloud_storage attachment should rendered it as a link in the outgoing email.",
            )

        # A cloud attachment and small txt attachment sent -> 1st should become a link, 2nd should be sent with the message
        small_attachment = self.env["ir.attachment"].create({
            "name": "Small attachment that should be attached normally.txt",
            "datas": base64.b64encode(b"tiny file").decode(),
            "mimetype": "text/plain",
            "res_model": "res.partner",
            "res_id": thread_model.id,
        })

        composer_form = Form(self.env['mail.compose.message'].with_context(
            default_model='res.partner',
            default_res_ids=thread_model.ids,
            default_composition_mode='comment',
            default_force_send=True,
            default_partner_ids=partners.ids,
        ))
        composer_form.attachment_ids.add(small_attachment)
        composer_form.attachment_ids.add(cloud_attachment)
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()

        self.assertEqual(len(self._mails), 2)
        body = self._mails[0]['body']
        for mail in self._mails:
            self.assertEqual(len(mail['attachments']), 1,
                "There should be only one small attachment per message")
            self.assertIn(small_attachment.name, str(mail['attachments']),
                "Only text attachment should be sent in the message")

        for body, attachment in zip([m["body"] for m in self._mails], self._new_mails.attachment_ids):
            large_attachment_link = str(self.env["ir.qweb"]._render("mail.mail_attachment_links", {"attachments": cloud_attachment}))
            self.assertEqual(body.count(large_attachment_link), 1,
                    "Sending mail with cloud_storage attachment should rendered it as a link in the outgoing email.",
            )

        # A large txt attachment and 2 cloud attachments sent -> All 3 shall became links
        cloud_attachment2 = self.env["ir.attachment"].create({
            "name": "cloud2 attachment also should be attached as a link",
            "type": "cloud_storage",
            "url": "https://storage.googleapis.com/fakebucket/cloud2.txt",
            "res_model": "res.partner",
            "res_id": thread_model.id,
        })

        max_email_size_bytes = self.env['ir.mail_server'].sudo()._get_max_email_size() * 1024 * 1024
        too_much_bytes = b"x" * (int(max_email_size_bytes) + 1)
        large_attachment = self.env["ir.attachment"].create({
            "name": "persistent large attachment should be attached as a link",
            "datas": base64.b64encode(too_much_bytes).decode(),
            "mimetype": "text/plain",
            "res_model": "res.partner",
            "res_id": thread_model.id,
        })
        composer_form = Form(self.env['mail.compose.message'].with_context(
            default_model='res.partner',
            default_res_ids=thread_model.ids,
            default_composition_mode='comment',
            default_force_send=True,
            default_partner_ids=partners.ids,
        ))
        composer_form.attachment_ids.add(large_attachment)
        composer_form.attachment_ids.add(cloud_attachment)
        composer_form.attachment_ids.add(cloud_attachment2)
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()

        for body, attachment in zip([m["body"] for m in self._mails], self._new_mails.attachment_ids):
            cloud_attachment_present = body.count(cloud_attachment.access_token) == body.count(cloud_attachment.name) == 1
            cloud_attachment2_present = body.count(cloud_attachment2.access_token) == body.count(cloud_attachment2.name) == 1
            large_attachment_link = str(self.env["ir.qweb"]._render("mail.mail_attachment_links", {"attachments": large_attachment}))
            self.assertTrue(body.count(large_attachment_link) == 1 and cloud_attachment_present and cloud_attachment2_present,
                "Two cloud and one large attachments should be converted and sent as links in the outgoing email.",
            )

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
