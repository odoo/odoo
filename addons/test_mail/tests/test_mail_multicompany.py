# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import socket

from itertools import product
from freezegun import freeze_time
from unittest.mock import patch
from werkzeug.urls import url_parse

from odoo.addons.mail.models.mail_message import Message
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.models.test_mail_corner_case_models import MailTestMultiCompanyWithActivity
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.exceptions import AccessError
from odoo.tests import tagged, users, HttpCase
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

        _original_car = Message._check_access
        with patch.object(Message, '_check_access',
                          autospec=True, side_effect=_original_car) as mock_msg_car:
            with self.assertRaises(AccessError):
                test_records_mc_c1.message_post(
                    body='<p>Hello</p>',
                    message_type='comment',
                    record_name='CustomName',  # avoid ACL on display_name
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
            message_type='comment',
            parent_id=initial_message.id,
            record_name='CustomName',  # avoid ACL on display_name
            reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
            subtype_xmlid='mail.mt_comment',
        )

        # now able to post as was notified of parent message
        attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(
                2, 'mail.compose.message', 0,
                prefix='Other'
            )
        )
        # record_name and reply_to may generate ACLs issues when computed by
        # 'message_post' but should not, hence not specifying them to be sure
        # testing the complete flow
        test_records_mc_c1.message_post(
            attachments=attachments_data,
            attachment_ids=attachments.ids,
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
            message_type='comment',
            record_name='CustomName',  # avoid ACL on display_name
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
                message_type='comment',
                record_name='CustomName',  # avoid ACL on display_name
                reply_to='custom.reply.to@test.example.com',  # avoid ACL in notify_get_reply_to
                subtype_xmlid='mail.mt_comment',
            )

    def test_recipients_multi_company(self):
        """Test mentioning a partner with no common company."""
        test_records_mc_c2 = self.test_records_mc[1]
        self._reset_bus()
        with self.assertBus([(self.cr.dbname, "res.partner", self.user_employee_c3.partner_id.id)]):
            test_records_mc_c2.with_user(self.user_employee_c2).with_context(
                allowed_company_ids=self.company_2.ids
            ).message_post(
                body="Hello @Freudenbergerg",
                message_type="comment",
                partner_ids=self.user_employee_c3.partner_id.ids,
                subtype_xmlid="mail.mt_comment",
            )

    @freeze_time('2023-11-22 08:00:00')
    @users("admin")
    def test_systray_get_activities(self):
        original_check_access = MailTestMultiCompanyWithActivity._check_access
        user_admin = self.user_admin.with_user(self.user_admin)
        user_employee = self.user_employee.with_user(self.user_employee)
        company_1_all = user_admin.company_id
        company_2_admin_only = self.company_2
        test_model_name = 'mail.test.multi.company.with.activity'
        activity_type_todo = 'test_mail.mail_act_test_todo'

        def _mock_check_access(records, operation):
            """ To avoid creating a new test model not accessible by employee user, we modify the access rules. """
            result = original_check_access(records, operation)
            if records.env.uid == self.user_admin.id:
                return result
            forbidden = result[0] if result else records.browse()
            forbidden += (records - forbidden).filtered(lambda record: record.create_uid != user_employee)
            if forbidden:
                return (forbidden, lambda: AccessError("Nope"))
            return None

        user_records = self.env[test_model_name].with_user(user_employee).sudo().create([
            {"name": "Test1", "company_id": company_1_all.id},
            {"name": "Test2", "company_id": company_2_admin_only.id},
        ])
        admin_records = self.env[test_model_name].create([
            {"name": "TestAdmin1", "company_id": company_1_all.id},
            {"name": "TestAdmin2", "company_id": company_2_admin_only.id},
            {"name": "TestAdmin3", "company_id": False},
        ])
        # Schedule an employee and admin todo activity for each records
        admin_activities_on_user_records = self.env['mail.activity'].concat(
            *(record.activity_schedule(activity_type_todo, user_id=user_admin.id) for record in user_records))
        admin_activities_on_admin_records = self.env['mail.activity'].concat(
            *(record.activity_schedule(activity_type_todo, user_id=user_admin.id) for record in admin_records))
        admin_activities_all = admin_activities_on_user_records | admin_activities_on_admin_records
        user_activities_on_user_records = self.env['mail.activity'].concat(
            *(record.activity_schedule(activity_type_todo, user_id=user_employee.id) for record in user_records))
        user_activities_on_admin_records = self.env['mail.activity'].concat(
            *(record.activity_schedule(activity_type_todo, user_id=user_employee.id) for record in admin_records))

        self.assertTrue((company_1_all | company_2_admin_only) <= user_admin.company_ids)
        self.assertEqual(company_1_all, user_employee.company_ids)

        # We test the outcome of systray_get_activities for different couple of user and allowed companies
        for (user, allowed_company_ids), (expected_other_activities, expected_test_model_activities) in (
                (
                        # Admin see only activities of records of allowed companies (company_1).
                        (user_admin, company_1_all.ids),
                        (False, admin_activities_on_user_records[0] +
                                admin_activities_on_admin_records[0] + admin_activities_on_admin_records[2]),
                ),
                (
                        # Admin see only activities of records of allowed companies (company_2).
                        (user_admin, company_2_admin_only.ids),
                        (False, admin_activities_on_user_records[1] +
                                admin_activities_on_admin_records[1] + admin_activities_on_admin_records[2]),
                ),
                (
                        # Admin see only activities of records of allowed companies (company_1 and company_2).
                        (user_admin, (company_1_all | company_2_admin_only).ids),
                        (False, admin_activities_all),
                ),
                (
                        # Employee see all activities of records of allowed companies (company_1) he has access to,
                        # and under "Other activities", see all activities of allowed companies he has not access to
                        # + activities related to record with company False or he has not access to.
                        (user_employee, company_1_all.ids),
                        # No access to admin_records nor the user_records[1] (bound to company_2 he has no access)
                        (user_activities_on_admin_records + user_activities_on_user_records[1],
                         user_activities_on_user_records[0]),
                ),
        ):
            with self.subTest(user=user, allowed_company_ids=allowed_company_ids):
                self.authenticate(user.login, user.login)
                with patch.object(MailTestMultiCompanyWithActivity, '_check_access', autospec=True,
                                  side_effect=_mock_check_access):
                    activity_groups = self.make_jsonrpc_request("/mail/data", {
                        "systray_get_activities": True,
                        "context": {"allowed_company_ids": allowed_company_ids}
                    })["Store"]["activityGroups"]
                activity_groups_by_model = {ag["model"]: ag for ag in activity_groups}
                other_activities_model_name = 'mail.activity'
                if expected_other_activities:
                    self.assertIn(other_activities_model_name, activity_groups_by_model)
                    activity_group = activity_groups_by_model[other_activities_model_name]
                    self.assertDictEqual(
                        {
                            "type": "activity",
                            "view_type": "list",
                            "overdue_count": 0,
                            "planned_count": 0,
                            "today_count": len(expected_other_activities),
                            "total_count": len(expected_other_activities),
                            "id": self.env["ir.model"]._get_id(other_activities_model_name),
                            "model": other_activities_model_name,
                            "name": "Other activities",
                            "icon": "/mail/static/description/icon.png",
                            "activity_ids": set(expected_other_activities.ids),
                        },
                        {
                            **activity_group,
                            # To compare regardless the order
                            "activity_ids": set(activity_group['activity_ids']),
                        }
                    )
                else:
                    self.assertNotIn(other_activities_model_name, activity_groups_by_model)
                self.assertIn(test_model_name, activity_groups_by_model)
                self.assertDictEqual(
                    {
                        "type": "activity",
                        "view_type": "list",
                        "overdue_count": 0,
                        "planned_count": 0,
                        "today_count": len(expected_test_model_activities),
                        "total_count": len(expected_test_model_activities),
                        "id": self.env["ir.model"]._get_id(test_model_name),
                        "model": test_model_name,
                        "name": "Test Multi Company Mail With Activity",
                        "icon": "/base/static/description/icon.png",
                    },
                    activity_groups_by_model[test_model_name])
        # Activities related to not accessible records are in other activities regardless of the allowed companies
        self.authenticate(user_admin.login, user_admin.login)
        with patch.object(MailTestMultiCompanyWithActivity, '_check_access', autospec=True,
                          side_effect=lambda self, operation: (self, lambda: AccessError("Nope"))):
            for companies in (company_1_all, company_2_admin_only, company_1_all | company_2_admin_only):
                with self.subTest(companies=companies):
                    activity_groups = self.make_jsonrpc_request("/mail/data", {
                        "systray_get_activities": True,
                        "context": {"allowed_company_ids": companies.ids}
                    })["Store"]["activityGroups"]
                    other_activity_group = next(ag for ag in activity_groups if ag['model'] == 'mail.activity')
                    self.assertEqual(other_activity_group["total_count"], 5)


@tagged('-at_install', 'post_install', 'multi_company')
class TestMultiCompanyRedirect(MailCommon, HttpCase):

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
                    self.assertTrue('cids' in response.request._cookies)
                    self.assertEqual(response.request._cookies.get('cids'), str(mc_record.company_id.id))
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

        self.authenticate('admin', 'admin')
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

        # when being not logged, cids should be added based on
        # '_get_redirect_suggested_company'
        for test_record in nothreads:
            with self.subTest(record_name=test_record.name, user_company=user_company):
                self.authenticate(None, None)
                self.user_admin.write({'company_id': user_company.id})
                response = self.url_open(
                    f'/mail/view?model={test_record._name}&res_id={test_record.id}',
                    timeout=15
                )
                self.assertEqual(response.status_code, 200)

                if test_record.company_id:
                    self.assertIn('cids', response.request._cookies)
                    self.assertEqual(response.request._cookies.get('cids'), str(test_record.company_id.id))
                else:
                    self.assertNotIn('cids', response.request._cookies)
