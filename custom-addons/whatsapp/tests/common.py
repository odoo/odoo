# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import time

from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.base.models.res_partner import Partner
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.models.whatsapp_message import WhatsAppMessage
from odoo.addons.whatsapp.tests.template_data import template_data
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.tests import common, Form


class MockOutgoingWhatsApp(common.BaseCase):
    """ Mock calls to WhatsApp API, provide tools and patch to know what happens
    when contacting it. """

    @contextmanager
    def mockWhatsappGateway(self):
        self._init_wa_mock()
        wa_msg_origin = WhatsAppMessage.create
        partner_create_origin = Partner.create

        # ------------------------------------------------------------
        # Whatsapp API
        # ------------------------------------------------------------

        def _get_all_template():
            return template_data

        def _get_template_data(wa_template_uid):
            for tmpl in template_data["data"]:
                if tmpl["id"] == wa_template_uid:
                    return tmpl
            return {}

        def _send_whatsapp(number, *, send_vals, **kwargs):
            if send_vals:
                msg_uid = f'test_wa_{time.time():.9f}'
                self._wa_msg_sent.append(msg_uid)
                return msg_uid
            raise WhatsAppError("Please make sure to define a template before proceeding.")

        def _submit_template_new(json_data):
            if json_data:
                return {
                    "id": f"{time.time():.15f}",
                    "status": "PENDING",
                    "category": "MARKETING",
                }
            raise WhatsAppError("Please make sure to define a template before proceeding.")

        def _upload_demo_document(attachment):
            if attachment:
                return "2:c2SpecFlow6karmaFsdWU="
            raise WhatsAppError("There is no attachment to upload.")

        def _upload_whatsapp_document(attachment):
            if attachment:
                return {
                    "messaging_product": "whatsapp",
                    "contacts": [{
                            "input": self.whatsapp_account,
                            "wa_id": "1234567890",
                        }],
                    "messages": [{
                        "id": "qwertyuiop0987654321",
                    }]
                }
            raise WhatsAppError("Please ensure you are using the correct file type and try again.")

        def _get_header_data_from_handle(url):
            if url == 'demo_image_url':
                return b'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==', 'image/jpeg'
            raise WhatsAppError("Please ensure you are using the correct file type and try again.")

        # ------------------------------------------------------------
        # Whatsapp Models
        # ------------------------------------------------------------

        def _res_partner_create(model, *args, **kwargs):
            records = partner_create_origin(model, *args, **kwargs)
            self._new_partners += records.sudo()
            return records

        def _wa_message_create(model, *args, **kwargs):
            res = wa_msg_origin(model, *args, **kwargs)
            self._new_wa_msg += res.sudo()
            return res

        try:
            with patch.object(Partner, 'create', autospec=True, wraps=Partner, side_effect=_res_partner_create), \
                 patch.object(WhatsAppApi, '_get_all_template', side_effect=_get_all_template), \
                 patch.object(WhatsAppApi, '_get_template_data', side_effect=_get_template_data), \
                 patch.object(WhatsAppApi, '_upload_demo_document', side_effect=_upload_demo_document), \
                 patch.object(WhatsAppApi, '_upload_whatsapp_document', side_effect=_upload_whatsapp_document), \
                 patch.object(WhatsAppApi, '_send_whatsapp', side_effect=_send_whatsapp), \
                 patch.object(WhatsAppApi, '_submit_template_new', side_effect=_submit_template_new), \
                 patch.object(WhatsAppApi, '_get_header_data_from_handle', side_effect=_get_header_data_from_handle), \
                 patch.object(WhatsAppMessage, 'create', autospec=True, wraps=WhatsAppMessage, side_effect=_wa_message_create):
                yield
        finally:
            pass

    def _init_wa_mock(self):
        self._new_partners = self.env['res.partner'].sudo()
        self._new_wa_msg = self.env['whatsapp.message'].sudo()
        self._wa_msg_sent = []


class MockIncomingWhatsApp(common.HttpCase):
    """ Mock and provide tools on incoming WhatsApp calls. """

    # ------------------------------------------------------------
    # TOOLS FOR SIMULATING RECEPTION
    # ------------------------------------------------------------

    def _get_message_signature(self, account, message_data):
        return hmac.new(
            account.app_secret.encode(),
            msg=message_data.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _receive_message_update(self, account, display_phone_number, extra_value=None):
        """ Simulate reception of a message update from WhatsApp API.

        param account: whatsapp.account
        param display_phone_number: phone number from which message was created
          (e.g. "+91 12345 67891")
        param extra_value: extra data added in "value" of "changes", to send in the request
          (e.g. "statuses": [{"status": "failed"}, ...])
        """
        data = json.dumps({
            "entry": [{
                "id": account.account_uid,
                "changes": [{
                    "field": "messages",
                    "value": dict(
                        {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": display_phone_number,
                                "phone_number_id": account.phone_uid,
                            },
                        }, **(extra_value or {}))
                }]
            }]
        })

        return self._make_webhook_request(
            account,
            message_data=data,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={self._get_message_signature(account, data)}",
            }
        )

    def _receive_template_update(self, field, account, data):
        """ Simulate reception of a template update from WhatsApp API.

        param field: field to update (e.g. "message_template_status_update")
        param account: whatsapp.account
        param data: data to send in the request (e.g. {"event": "APPROVED"})
        """
        data = json.dumps({
            "entry": [{
                "id": account.account_uid,
                "changes": [
                    {
                        "field": field,
                        "value": data,
                    }
                ]
            }]
        })

        return self._make_webhook_request(
            account,
            message_data=data,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={self._get_message_signature(account, data)}",
            }
        )

    def _receive_whatsapp_message(self, account, body, sender_phone_number, additional_message_values=None):
        message_data = json.dumps({
            "entry": [{
                "id": account.account_uid,
                "changes": [{
                    "field": "messages",
                    "value": {
                        "metadata": {"phone_number_id": account.phone_uid},
                        "messages": [
                            dict({
                                "id": f"test_wa_{time.time():.9f}",
                                "from": sender_phone_number,
                                "type": "text",
                                "text": {"body": body}
                            }, **(additional_message_values or {}))
                        ],
                    }
                }]
            }]
        })

        return self._make_webhook_request(
            account,
            message_data=message_data,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={self._get_message_signature(account, message_data)}",
            }
        )

    def _make_webhook_request(self, account, message_data=None, headers=None):
        if not message_data:
            message_data = json.dumps({'entry': [{'id': account.account_uid}]}).encode()
        return self.url_open(
            '/whatsapp/webhook/', data=message_data, headers={
                "Content-Type": "application/json",
                **(headers or {})
            }
        ).json()

    # ------------------------------------------------------------
    # TEST TOOLS AND ASSERTS
    # ------------------------------------------------------------

    def _find_discuss_channel(self, whatsapp_number):
        # Remove me in master, moved in WhatsAppCase
        return self.env["discuss.channel"].search([("whatsapp_number", "=", whatsapp_number)])

    def assertWhatsAppChannel(self, sender_phone_number):
        # Remove me in master, moved in WhatsAppCase
        discuss_channel = self._find_discuss_channel(sender_phone_number)
        self.assertEqual(len(discuss_channel), 1, f'Should find exactly one channel for number {sender_phone_number}')
        self.assertEqual(len(discuss_channel.message_ids), 1)
        return discuss_channel


class WhatsAppCase(MockOutgoingWhatsApp):
    """ Common class with tools and asserts """

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _add_button_to_template(self, template, name,
                                button_type='quick_reply', sequence=1,
                                call_number=False,
                                url_type=False,
                                website_url=False):
        template.write({
            'button_ids': [(0, 0, {
                'button_type': button_type if button_type else 'quick_reply',
                'call_number': call_number if call_number else '',
                'name': name,
                'sequence': sequence,
                'url_type': url_type if url_type else 'static',
                'wa_template_id': template.id,
                'website_url': website_url if website_url else '',
            })],
        })

    def _wa_composer_form(self, template, from_records, with_user=False,
                          add_context=None):
        """ Create a whatsapp composer form, intended to run 'template' on
        'from_records'.

        :param with_user: a user to set on environment, allowing to check ACLs;
        :param add_context: optional additional context values given to the
          composer creation;
        """
        context = dict(
            {
                'active_model': from_records._name,
                'active_ids': from_records.ids,
                'default_wa_template_id': template.id,
            }, **(add_context or {})
        )
        return Form(self.env['whatsapp.composer'].with_context(context).with_user(with_user or self.env.user))

    def _instanciate_wa_composer_from_records(self, template, from_records,
                                              with_user=False,
                                              add_context=None):
        """ Create a whatsapp composer to run 'template' on 'from_records'.

        :param with_user: a user to set on environment, allowing to check ACLs;
        :param add_context: optional additional context values given to the
          composer creation;
        """
        context = dict(
            {'active_model': from_records._name, 'active_ids': from_records.ids},
            **(add_context or {})
        )
        return self.env['whatsapp.composer'].with_context(context).with_user(with_user or self.env.user).create({
            'wa_template_id': template.id,
        })

    # ------------------------------------------------------------
    # MESSAGE FIND AND ASSERTS
    # ------------------------------------------------------------

    def _find_wa_msg_wnumber(self, mobile_number):
        """ Find a WA message, based on 'mobile_number' """
        for wa_msg in self._new_wa_msg:
            if wa_msg.mobile_number == mobile_number:
                return wa_msg
        debug_info = '\n'.join(
            f'From: {wa_msg.mobile_number} (ID {wa_msg.id})'
            for wa_msg in self._new_wa_msg
        )
        raise AssertionError(
            f'whatsapp.message not found for number {mobile_number}\n{debug_info})'
        )

    def _find_wa_msg_wrecord(self, record):
        """ Find a WA message, using linked record through its mail.message """
        for wa_msg in self._new_wa_msg:
            if wa_msg.mail_message_id.model == record._name and wa_msg.mail_message_id.res_id == record.id:
                return wa_msg
        debug_info = '\n'.join(
            f'From: {wa_msg.mobile_number} (ID {wa_msg.id})'
            for wa_msg in self._new_wa_msg
        )
        raise AssertionError(
            f'whatsapp.message not found for record {record.display_name} ({record._name}/{record.id}\n{debug_info})'
        )

    def _assertWAMessage(self, wa_message, status='sent',
                         fields_values=None, attachment_values=None,
                         mail_message_values=None):
        """ Assert content of WhatsApp message.

        :param <whatsapp.message> wa_message: whatsapp message whose content
          is going to be checked;
        :param str status: one of whatsapp.message.state field value;
        :param dict fields_values: if given, should be a dictionary of field
          names / values allowing to check message content (e.g. body);
        :param dict attachment_values: if given, should be a dictionary of field
          names / values allowing to check attachment values (e.g. mimetype);
        :param dict mail_message_values: if given, should be a dictionary of
          field names/values to check inner mail.message content;
        """
        if len(wa_message) != 1:
            debug_info = '\n'.join(
                f'Msg: {wa_msg.id}, {wa_msg.body}'
                for wa_msg in wa_message
            )
            raise AssertionError(
                f'whatsapp.message: should have 1 message, received {len(wa_message)}\n{debug_info}'
            )

        # check base message data
        self.assertEqual(
            wa_message.state, status,
            f'whatsapp.message invalid status: found {wa_message.state}, expected {status}')

        # check message content
        for fname, fvalue in (fields_values or {}).items():
            with self.subTest(fname=fname, fvalue=fvalue):
                self.assertEqual(
                    wa_message[fname], fvalue,
                    f'whatsapp.message: expected {fvalue} for {fname}, got {wa_message[fname]}'
                )

        # check inner mail.message content
        for fname, fvalue in (mail_message_values or {}).items():
            with self.subTest(fname=fname, fvalue=fvalue):
                self.assertEqual(
                    wa_message.mail_message_id[fname], fvalue,
                    f'whatsapp.message mail_message_id: expected {fvalue} for {fname}, got {wa_message.mail_message_id[fname]}'
                )

        if attachment_values:
            # check attachment values
            attachment = wa_message.mail_message_id.attachment_ids
            # only support one attachment for whatsapp messages
            self.assertEqual(len(attachment), 1)

            for fname, fvalue in (attachment_values).items():
                with self.subTest(fname=fname, fvalue=fvalue):
                    attachment_value = attachment[fname]
                    self.assertEqual(
                        attachment_value, fvalue,
                        f'whatsapp.message invalid attachment: expected {fvalue} for {fname}, got {attachment_value}'
                    )

    def assertWAMessage(self, status='sent', fields_values=None,
                        attachment_values=None, mail_message_values=None):
        """ Assert and check content of a unique whatsapp message created under
        mock. """
        self._assertWAMessage(
            self._new_wa_msg, status=status,
            fields_values=fields_values,
            attachment_values=attachment_values,
            mail_message_values=mail_message_values,
        )

    def assertWAMessageFromNumber(self, mobile_number,
                                  status='sent', fields_values=None,
                                  attachment_values=None, mail_message_values=None):
        """ Assert and check content of a whatsapp message fetched based on a
        given mobile number. """
        whatsapp_message = self._find_wa_msg_wnumber(mobile_number)
        self._assertWAMessage(
            whatsapp_message, status=status,
            fields_values=fields_values,
            attachment_values=attachment_values,
            mail_message_values=mail_message_values,
        )

    def assertWAMessageFromRecord(self, record,
                                  status='sent', fields_values=None,
                                  attachment_values=None, mail_message_values=None):
        """ Assert and check content of a whatsapp message fetched based on a
        given record. """
        whatsapp_message = self._find_wa_msg_wrecord(record)
        self._assertWAMessage(
            whatsapp_message, status=status,
            fields_values=fields_values,
            attachment_values=attachment_values,
            mail_message_values=mail_message_values,
        )

    # ------------------------------------------------------------
    # DISCUSS ASSERTS
    # ------------------------------------------------------------

    def _find_wa_discuss_channel(self, whatsapp_number, wa_account=None, channel_domain=None):
        domain = [("whatsapp_number", "=", whatsapp_number)]
        if wa_account:
            domain += [("wa_account_id", "=", wa_account.id)]
        if channel_domain:
            domain += channel_domain
        return self.env["discuss.channel"].search(domain)

    def _assertWADiscussChannel(self, channel, wa_msg_count=1, msg_count=1,
                                channel_values=None):
        self.assertEqual(len(channel.message_ids), msg_count)
        self.assertEqual(len(channel.message_ids.wa_message_ids), wa_msg_count)

        for fname, fvalue in (channel_values or {}).items():
            with self.subTest(fname=fname, fvalue=fvalue):
                self.assertEqual(
                    channel[fname], fvalue,
                    f'discuss.channel: expected {fvalue} for {fname}, got {channel[fname]}'
                )

    def assertWhatsAppDiscussChannel(self, sender_phone_number, wa_account=None,
                                     channel_domain=None,
                                     channel_values=None,
                                     new_partner_values=None,
                                     wa_msg_count=1, msg_count=1,
                                     wa_message_fields_values=None,
                                     wa_message_attachments_values=None,
                                     wa_mail_message_values=None):
        discuss_channel = self._find_wa_discuss_channel(
            sender_phone_number, wa_account=wa_account, channel_domain=channel_domain
        )
        self.assertEqual(len(discuss_channel), 1, f'Should find exactly one channel for number {sender_phone_number}')

        # check partner created during mock
        if new_partner_values:
            partner = self._new_partners
            self.assertEqual(len(partner), 1, 'Should have created a new partner during mock')
            for fname, fvalue in new_partner_values.items():
                with self.subTest(fname=fname, fvalue=fvalue):
                    self.assertEqual(
                        partner[fname], fvalue,
                        f'res.partner: expected {fvalue} for {fname}, got {partner[fname]}'
                    )
            self.assertEqual(discuss_channel.whatsapp_partner_id, partner)

        self._assertWADiscussChannel(
            discuss_channel, wa_msg_count=wa_msg_count, msg_count=msg_count,
            channel_values=channel_values)

        self.assertWAMessage(
            status=(wa_message_fields_values or {}).get('state', 'received'),
            fields_values=wa_message_fields_values,
            attachment_values=wa_message_attachments_values,
            mail_message_values=wa_mail_message_values,
        )
        return discuss_channel

    # ------------------------------------------------------------
    # TEMPLATE ASSERTS
    # ------------------------------------------------------------

    def assertWATemplate(self, template, status='pending',
                         fields_values=None, attachment_values=None,
                         template_variables=None, template_variables_strict=True):
        """ Assert content of WhatsApp template.

        :param <whatsapp.template> template: whatsapp template whose content
          is going to be checked;
        :param str status: one of whatsapp.template.status field value;
        :param dict fields_values: if given, should be a dictionary of field
          names / values allowing to check template content (e.g. body);
        :param dict attachment_values: if given, should be a dictionary of field
          names / values allowing to check attachment values (e.g. mimetype);
        :param list template_variables: see 'assertWATemplateVariables';
        :param boolean template_variables_strict: see 'assertWATemplateVariables';
        """
        # check base template data
        self.assertEqual(template.status, status,
                         f'whatsapp.template invalid status: found {template.status}, expected {status}')

        # check template content
        for fname, fvalue in (fields_values or {}).items():
            with self.subTest(fname=fname, fvalue=fvalue):
                self.assertEqual(
                    template[fname], fvalue,
                    f'whatsapp.template: expected {fvalue} for {fname}, got {template[fname]}'
                )

        if attachment_values:
            # check attachment values
            attachment = template.header_attachment_ids
            # only support one attachment for whatsapp templates
            self.assertEqual(len(attachment), 1, 'whatsapp.template: should have only one attachment')

            for fname, fvalue in (attachment_values).items():
                with self.subTest(fname=fname, fvalue=fvalue):
                    attachment_value = attachment[fname]
                    self.assertEqual(
                        attachment_value, fvalue,
                        f'whatsapp.template invalid attachment: expected {fvalue} for {fname}, got {attachment_value}'
                    )
        if template_variables:
            self.assertWATemplateVariables(template, template_variables, strict=template_variables_strict)

    def assertWATemplateVariables(self, template, expected_variables, strict=True):
        """ Assert content of 'variable_ids' field of a template

        :param list expected_variables: values of variables expected in template;
        :param bool strict: in addition to content ensure there are no other
          variables;
        """
        for (exp_name, exp_line_type, exp_field_type, exp_vals) in expected_variables:
            with self.subTest(exp_name=exp_name):
                exp_demo_value = exp_vals.get('demo_value')
                tpl_variable = template.variable_ids.filtered(
                    lambda v: (
                        v.name == exp_name and v.line_type == exp_line_type and
                        (not exp_demo_value or v.demo_value == exp_demo_value)
                    )
                )
                if not tpl_variable or len(tpl_variable) > 1:
                    notfound_msg = f'Not found variable for {exp_name} / {exp_line_type}'
                    if exp_demo_value:
                        notfound_msg += f' (demo value {exp_demo_value})'
                    existing = '\n'.join(
                        f'{var.name} / {var.line_type} (demo: {var.demo_value})'
                        for var in template.variable_ids
                    )
                    notfound_msg += f'\n{existing}'
                    self.assertTrue(tpl_variable and len(tpl_variable) == 1, notfound_msg)
                self.assertEqual(tpl_variable.field_type, exp_field_type)
                self.assertEqual(tpl_variable.line_type, exp_line_type)
                for fname, fvalue in (exp_vals or {}).items():
                    self.assertEqual(tpl_variable[fname], fvalue)
        if strict:
            self.assertEqual(len(template.variable_ids), len(expected_variables))


class WhatsAppCommon(MailCommon, WhatsAppCase):
    """ Bootstrap data for tests """

    @classmethod
    def setUpClass(cls):
        """ Note that MailCommon is multi-company by default """
        super().setUpClass()

        # ensure company / users data for tests, don't rely on demo
        cls.company_admin.write({
            'country_id': cls.env.ref('base.us'),
            'name': 'Main Test Company',
        })
        cls.user_admin.write({
            'country_id': cls.env.ref('base.be'),
        })

        # phone-specific test data
        cls.user_employee_mobile = '+91(132)-553-7272'
        cls.user_employee.mobile = cls.user_employee_mobile

        # Notified user for WhatsApp Business Account
        cls.user_wa_admin = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref('base.in').id,
            email='wa_admin@test.example.com',
            groups='base.group_user,base.group_partner_manager,whatsapp.group_whatsapp_admin',
            login='user_wa_admin',
            mobile='+91(132)-553-7242',
            name='WhatsApp Wasin',
            notification_type='email',
            phone='+1 650-555-0111',
            signature='--\nWasin'
        )
        # WhatsApp Business Accounts
        cls.whatsapp_account, cls.whatsapp_account_2 = cls.env['whatsapp.account'].with_user(cls.user_admin).create([
            {
                'account_uid': 'abcdef123456',
                'app_secret': '1234567890abcdef',
                'app_uid': 'contact',
                'name': 'odoo account',
                'notify_user_ids': cls.user_wa_admin.ids,
                'phone_uid': '1234567890',
                'token': 'team leader',
            },
            {
                'account_uid': 'ghijkl789',
                'app_secret': '789ghijkl',
                'app_uid': 'contact2',
                'name': 'odoo account 2',
                'notify_user_ids': cls.user_wa_admin.ids,
                'phone_uid': '0987654321',
                'token': 'token_2',
            }
        ])
        # Test customer (In)
        cls.whatsapp_customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.in').id,
            'email': 'wa.customer.in@test.example.com',
            'name': 'Wa Customer In',
            'phone': "+91 12345 67891"
        })

        # https://github.com/mathiasbynens/small
        image_data = ("/9j/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8Q"
                      "EBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=")
        pdf_data = ("JVBERi0xLgoxIDAgb2JqPDwvUGFnZXMgMiAwIFI+PmVuZG9iagoyIDAgb2JqPDwvS2lkc1szIDAg"
                    "Ul0vQ291bnQgMT4+ZW5kb2JqCjMgMCBvYmo8PC9QYXJlbnQgMiAwIFI+PmVuZG9iagp0cmFpbGVy"
                    "IDw8L1Jvb3QgMSAwIFI+Pg==")
        video_data = ("AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAAhtZGF0AAAA1m1vb3YA"
                      "AABsbXZoZAAAAAAAAAAAAAAAAAAAA+gAAAAAAAEAAAEAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAA"
                      "AAAAAQAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAABidWR0"
                      "YQAAAFptZXRhAAAAAAAAACFoZGxyAAAAAAAAAABtZGlyYXBwbAAAAAAAAAAAAAAAAC1pbHN0AAAA"
                      "Jal0b28AAAAdZGF0YQAAAAEAAAAATGF2ZjU3LjQxLjEwMA==")
        documents = cls.env['ir.attachment'].with_user(cls.user_employee).create([
            {'name': 'Document.pdf', 'datas': pdf_data},
            {'name': 'Image.jpg', 'datas': image_data},
            {'name': 'Video.mp4', 'datas': video_data},
            {'name': 'Payload.wasm', 'datas': "AGFzbQEAAAA=", 'mimetype': 'application/octet-stream'},
        ])
        cls.document_attachment, cls.image_attachment, cls.video_attachment, cls.invalid_attachment = documents
        documents_wa_admin = cls.env['ir.attachment'].with_user(cls.user_wa_admin).create([
            {'name': 'Document.pdf', 'datas': pdf_data},
            {'name': 'Image.jpg', 'datas': image_data},
            {'name': 'Video.mpg', 'datas': video_data},
            {'name': 'Payload.wasm', 'datas': "AGFzbQEAAAA=", 'mimetype': 'application/octet-stream'},
        ])
        cls.document_attachment_wa_admin, cls.image_attachment_wa_admin, cls.video_attachment_wa_admin, cls.invalid_attachment_wa_admin = documents_wa_admin

    @classmethod
    def _setup_share_users(cls):
        cls.test_portal_user = mail_new_test_user(
            cls.env,
            login='test_portal_user',
            mobile='+32 494 12 34 56',
            phone='+32 494 12 34 89',
            name='Portal User',
            email='portal@test.example.com',
            groups='base.group_portal',
        )
        cls.test_public_user = mail_new_test_user(
            cls.env,
            login='test_public_user',
            mobile='+32 494 65 43 21',
            phone='+32 494 98 43 21',
            name='Public User',
            email='public@test.example.com',
            groups='base.group_public',
        )
