# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import socket

from itertools import product
from freezegun import freeze_time
from unittest.mock import patch
from werkzeug.urls import url_parse

from odoo.addons.mail.models.mail_message import MailMessage
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.test_mail.models.test_mail_corner_case_models import MailTestMultiCompanyWithActivity
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.exceptions import AccessError
from odoo.tests import tagged, users, HttpCase
from odoo.tests.common import JsonRpcException
from odoo.tools import mute_logger


class TestMailMCCommon(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_model = cls.env['ir.model']._get('mail.test.gateway')
        cls.email_from = '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>'

        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})
        cls.test_records_mc = cls.env['mail.test.multi.company'].create([
            {'name': 'Test Company1',
             'company_id': cls.user_employee.company_id.id},
            {'name': 'Test Company2',
             'company_id': cls.user_employee_c2.company_id.id},
        ])

        cls.partner_1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        # groups@.. will cause the creation of new mail.test.gateway
        cls.mail_alias = cls.env['mail.alias'].create({
            'alias_contact': 'everyone',
            'alias_model_id': cls.test_model.id,
            'alias_name': 'groups',
        })

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls.env['mail.message'].create({
            'model': 'mail.test.gateway',
            'res_id': cls.test_record.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'subtype_id': cls.env.ref('mail.mt_comment').id,
            'author_id': cls.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.test.gateway@%s>' % (cls.test_record.id, socket.gethostname()),
        })

        cls._create_portal_user()
        cls.user_portal_c2 = mail_new_test_user(
            cls.env,
            groups='base.group_portal',
            login='portal_user_c2',
            company_id=cls.company_2.id,
            name="Portal User C2",
        )

    def setUp(self):
        super().setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)


@tagged('multi_company')
class TestMultiCompanySetup(TestMailMCCommon, HttpCase):

    @users('employee_c2')
    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_post_with_read_access(self):
        """ Check that with readonly access, a message with attachment can be
        posted on a model with the attribute _mail_post_access = 'read'. """
        test_record_c1_su = self.env['mail.test.multi.company.read'].sudo().create([
            {
                'company_id': self.user_employee.company_id.id,
                'name': 'MC Readonly',
            }
        ])
        test_record_c1 = test_record_c1_su.with_env(self.env)
        self.assertFalse(test_record_c1.message_main_attachment_id)

        self.assertEqual(test_record_c1.name, 'MC Readonly')
        with self.assertRaises(AccessError):
            test_record_c1.write({'name': 'Cannot Write'})

        first_attachment = self.env['ir.attachment'].create({
            'company_id': self.user_employee_c2.company_id.id,
            'datas': base64.b64encode(b'First attachment'),
            'mimetype': 'text/plain',
            'name': 'TestAttachmentIDS.txt',
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })

        message = test_record_c1.message_post(
            attachments=[('testAttachment', b'First attachment')],
            attachment_ids=first_attachment.ids,
            body='My Body',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        self.assertTrue('testAttachment' in message.attachment_ids.mapped('name'))
        self.assertEqual(test_record_c1.message_main_attachment_id, first_attachment)

        new_attach = self.env['ir.attachment'].create({
            'company_id': self.user_employee_c2.company_id.id,
            'datas': base64.b64encode(b'Second attachment'),
            'mimetype': 'text/plain',
            'name': 'TestAttachmentIDS.txt',
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })
        message = test_record_c1.message_post(
            attachments=[('testAttachment', b'Second attachment')],
            attachment_ids=new_attach.ids,
            body='My Body',
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        self.assertEqual(
            sorted(message.attachment_ids.mapped('name')),
            ['TestAttachmentIDS.txt', 'testAttachment'],
        )
        self.assertEqual(test_record_c1.message_main_attachment_id, first_attachment)

    @users('employee_c2')
    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_post_wo_access(self):
        test_records_mc_c1, test_records_mc_c2 = self.test_records_mc.with_env(self.env)
        attachments_data = [
            ('ReportLike1', 'AttContent1'),
            ('ReportLike2', 'AttContent2'),
        ]

        # ------------------------------------------------------------
        # Other company (no access)
        # ------------------------------------------------------------

        _original_car = MailMessage._check_access
        with patch.object(MailMessage, '_check_access',
                          autospec=True, side_effect=_original_car) as mock_msg_car:
            with self.assertRaises(AccessError):
                test_records_mc_c1.message_post(
                    body='<p>Hello</p>',
                    force_record_name='CustomName',  # avoid ACL on display_name
                    message_type='comment',
                    reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
                    subtype_xmlid='mail.mt_comment',
                )
            self.assertEqual(mock_msg_car.call_count, 2,
                             'Check at model level succeeds and check at record level fails')
        with self.assertRaises(AccessError):
            _name = test_records_mc_c1.name

        # no access to company1, access to post through being notified of parent
        with self.assertRaises(AccessError):
            _subject = test_records_mc_c1.message_ids.subject
        self.assertEqual(len(self.test_records_mc[0].message_ids), 1)
        initial_message = self.test_records_mc[0].message_ids

        self.env['mail.notification'].sudo().create({
            'mail_message_id': initial_message.id,
            'notification_status': 'sent',
            'res_partner_id': self.user_employee_c2.partner_id.id,
        })
        # additional: works only if in partner_ids, not notified via followers
        initial_message.write({
            'partner_ids': [(4, self.user_employee_c2.partner_id.id)],
        })
        # now able to post as was notified of parent message
        test_records_mc_c1.message_post(
            body='<p>Hello</p>',
            force_record_name='CustomName',  # avoid ACL on display_name
            message_type='comment',
            parent_id=initial_message.id,
            reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
            subtype_xmlid='mail.mt_comment',
        )

        # record_name and reply_to may generate ACLs issues when computed by
        # 'message_post' but should not, hence not specifying them to be sure
        # testing the complete flow
        test_records_mc_c1.message_post(
            body='<p>Hello</p>',
            message_type='comment',
            parent_id=initial_message.id,
            subtype_xmlid='mail.mt_comment',
        )

        # ------------------------------------------------------------
        # User company (access granted)
        # ------------------------------------------------------------

        # can effectively link attachments with message to record of writable record
        attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(
                2, 'mail.compose.message', 0,
                prefix='Same'
            )
        )
        message = test_records_mc_c2.message_post(
            attachments=attachments_data,
            attachment_ids=attachments.ids,
            body='<p>Hello</p>',
            force_record_name='CustomName',  # avoid ACL on display_name
            message_type='comment',
            reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
            subtype_xmlid='mail.mt_comment',
        )
        self.assertTrue(attachments < message.attachment_ids)
        self.assertEqual(
            sorted(message.attachment_ids.mapped('name')),
            ['ReportLike1', 'ReportLike2', 'SameAttFileName_00.txt', 'SameAttFileName_01.txt'],
        )
        self.assertEqual(
            message.attachment_ids.mapped('res_id'),
            [test_records_mc_c2.id] * 4,
        )
        self.assertEqual(
            message.attachment_ids.mapped('res_model'),
            [test_records_mc_c2._name] * 4,
        )

        # cannot link attachments of unreachable records when posting on a document
        # they can access (aka no access delegation through posting message)
        attachments = self.env['ir.attachment'].sudo().create(
            self._generate_attachments_data(
                1,
                test_records_mc_c1._name,
                test_records_mc_c1.id,
                prefix='NoAccessMC'
            )
        )
        with self.assertRaises(AccessError):
            message = test_records_mc_c2.message_post(
                attachments=attachments_data,
                attachment_ids=attachments.ids,
                body='<p>Hello</p>',
                force_record_name='CustomName',  # avoid ACL on display_name
                message_type='comment',
                reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
                subtype_xmlid='mail.mt_comment',
            )

    def test_recipients_multi_company(self):
        """Test mentioning a partner with no common company."""
        test_records_mc_c2 = self.test_records_mc[1]
        with self.assertBus([(self.cr.dbname, "res.partner", self.user_employee_c3.partner_id.id)]):
            test_records_mc_c2.with_user(self.user_employee_c2).with_context(
                allowed_company_ids=self.company_2.ids
            ).message_post(
                body="Hello @Freudenbergerg",
                message_type="comment",
                partner_ids=self.user_employee_c3.partner_id.ids,
                subtype_xmlid="mail.mt_comment",
            )


@tagged('-at_install', 'post_install', 'multi_company', 'mail_controller')
class TestMultiCompanyControllers(TestMailMCCommon, HttpCase):

    @mute_logger('odoo.http')
    def test_mail_thread_data(self):
        """ Test returned thread data, in MC environment, to test notably MC
        access issues on partner, ACL support, ... """
        customer_c3 = self.env["res.partner"].create({
            "company_id": self.company_3.id,
            "name": "C3 Customer",
        })
        record = self.env["mail.test.multi.company.read"].with_user(self.user_employee_c2).create({
            "company_id": self.user_employee_c2.company_id.id,
            "name": "Multi Company Record",
        })
        self.assertEqual(record.company_id, self.company_2)

        record.message_subscribe(partner_ids=customer_c3.ids)
        with self.assertRaises(AccessError):
            customer_c3.with_user(self.user_employee_c2).check_access("read")

        self.authenticate(self.user_employee_c2.login, self.user_employee_c2.login)
        result = self.make_jsonrpc_request(
            "/mail/data", {"fetch_params": [["mail.thread", {
                "thread_id": record.id,
                "thread_model": record._name,
                "request_list": ["followers"],
            }]]},
        )
        self.assertEqual(len(result["mail.followers"]), 2)
        self.assertEqual(result["mail.followers"][0]["partner_id"], customer_c3.id)
        self.assertEqual(result["mail.thread"][0]["followersCount"], 2)
        self.assertTrue(result["mail.thread"][0]["hasWriteAccess"])
        self.assertTrue(result["mail.thread"][0]["hasReadAccess"])
        self.assertTrue(result["mail.thread"][0]["canPostOnReadonly"])

        # check read / write / post access info
        for test_user, (has_w, has_r, can_post) in zip(
            (self.user_portal, self.user_portal_c2, self.user_employee, self.user_admin),
            (
                (False, True, True),  # currently not really supported actually, should go through portal controllers
                (False, True, True),  # currently not really supported actually, should go through portal controllers
                (False, True, True),
                (True, True, True),
            ),
        ):
            with self.subTest(user_name=test_user.name):
                self.authenticate(test_user.login, test_user.login)
                # crash if calling using portal users -> dedicated portal routes currently
                if test_user in self.user_portal + self.user_portal_c2:
                    with self.assertRaises(JsonRpcException):
                        result = self.make_jsonrpc_request(
                            "/mail/data", {"fetch_params": [["mail.thread", {
                                "thread_id": record.id,
                                "thread_model": record._name,
                                "request_list": ["followers"],
                            }]]},
                        )
                else:
                    result = self.make_jsonrpc_request(
                        "/mail/data", {"fetch_params": [["mail.thread", {
                            "thread_id": record.id,
                            "thread_model": record._name,
                            "request_list": ["followers"],
                        }]]},
                    )
                    self.assertEqual(result["mail.thread"][0]["followersCount"], 2)
                    self.assertEqual(result["mail.thread"][0]["hasWriteAccess"], has_w)
                    self.assertEqual(result["mail.thread"][0]["hasReadAccess"], has_r)
                    self.assertEqual(result["mail.thread"][0]["canPostOnReadonly"], can_post)

    def test_redirect_to_records(self):
        """ Test mail/view redirection in MC environment, notably cids being
        added in redirect if user has access to the record. """
        mc_record_c1, mc_record_c2 = self.env['mail.test.multi.company'].create([
            {
                'company_id': self.user_employee.company_id.id,
                'name': 'Multi Company Record',
            },
            {
                'company_id': self.user_employee_c2.company_id.id,
                'name': 'Multi Company Record',
            }
        ])

        for (login, password), mc_record in product(
            ((None, None),  # not logged: redirect to web/login
             ('employee', 'employee'),  # access only main company
             ('admin', 'admin'),  # access both companies
            ),
            (mc_record_c1, mc_record_c2),
        ):
            with self.subTest(login=login, mc_record=mc_record):
                self.authenticate(login, password)
                response = self.url_open(
                    f'/mail/view?model={mc_record._name}&res_id={mc_record.id}',
                    timeout=15
                )
                self.assertEqual(response.status_code, 200)

                if not login:
                    path = url_parse(response.url).path
                    self.assertEqual(path, '/web/login')
                    self.assertNotIn('cids', response.request._cookies)
                else:
                    user = self.env['res.users'].browse(self.session.uid)
                    self.assertEqual(user.login, login)
                    mc_error = login == 'employee' and mc_record == mc_record_c2
                    if mc_error:
                        # Logged into company main, try accessing record in other
                        # company -> _redirect_to_record should redirect to
                        # messaging as the user doesn't have any access
                        parsed_url = url_parse(response.url)
                        self.assertEqual(parsed_url.path, '/odoo/action-mail.action_discuss')
                    else:
                        # Logged into company main, try accessing record in same
                        # company -> _redirect_to_record should add company in
                        # allowed_company_ids
                        cids = response.request._cookies.get('cids')
                        if mc_record.company_id == user.company_id:
                            self.assertEqual(cids, f'{mc_record.company_id.id}')
                        else:
                            self.assertEqual(cids, f'{user.company_id.id}-{mc_record.company_id.id}')

    def test_multi_redirect_to_records(self):
        """ Test mail/view redirection in MC environment, notably test a user that is
        redirected multiple times, the cids needed to access the record are being added
        recursivelly when in redirect."""
        mc_records = self.env['mail.test.multi.company'].create([
            {
                'company_id': self.user_employee.company_id.id,
                'name': 'Multi Company Record',
            },
            {
                'company_id': self.user_employee_c2.company_id.id,
                'name': 'Multi Company Record',
            }
        ])

        self.authenticate(self.user_admin.login, self.user_admin.login)
        companies = []
        for mc_record in mc_records:
            with self.subTest(mc_record=mc_record):
                response = self.url_open(
                    f'/mail/view?model={mc_record._name}&res_id={mc_record.id}',
                    timeout=15
                )
                self.assertEqual(response.status_code, 200)

                cids = response.request._cookies.get('cids')
                companies.append(str(mc_record.company_id.id))
                self.assertEqual(cids, '-'.join(companies))

    def test_redirect_to_records_nothread(self):
        """ Test no thread models and redirection """
        nothreads = self.env['mail.test.nothread'].create([
            {
                'company_id': company.id,
                'name': f'Test with {company.name}',
            }
            for company in (self.company_admin, self.company_2, self.env['res.company'])
        ])

        # when being logged, cids should be based on current user's company unless
        # there is an access issue (not tested here, see 'test_redirect_to_records')
        for test_record in nothreads:
            for user_company in self.company_admin, self.company_2:
                with self.subTest(record_name=test_record.name, user_company=user_company):
                    self.authenticate(self.user_admin.login, self.user_admin.login)
                    self.user_admin.write({'company_id': user_company.id})
                    response = self.url_open(
                        f'/mail/view?model={test_record._name}&res_id={test_record.id}',
                        timeout=15
                    )
                    self.assertEqual(response.status_code, 200)

                    self.assertTrue('cids' in response.request._cookies)
                    self.assertEqual(response.request._cookies.get('cids'), str(user_company.id))

        # when being not logged, cids should not be added as redirection after
        # logging will be 'mail/view' again
        for test_record in nothreads:
            with self.subTest(record_name=test_record.name):
                self.authenticate(None, None)
                response = self.url_open(
                    f'/mail/view?model={test_record._name}&res_id={test_record.id}',
                    timeout=15
                )
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('cids', response.request._cookies)
