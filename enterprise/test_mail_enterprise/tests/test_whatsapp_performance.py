# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.addons.whatsapp.tests.common import MockOutgoingWhatsApp, MockIncomingWhatsApp
from odoo.tests.common import users, warmup
from odoo.tests import tagged


@tagged('wa_performance', 'post_install', '-at_install')
class TestWAPerformance(BaseMailPerformance, MockOutgoingWhatsApp, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_employee.mobile = '+32 456 99 88 77'
        cls.customers[0].phone = '+32 456 00 11 22'
        cls.customers[1].phone = '+32 456 22 11 00'
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
        cls.wa_account = cls.env['whatsapp.account'].with_user(cls.user_admin).create({
            'account_uid': 'account_uid',
            'app_secret': 'app_secret',
            'app_uid': 'app_uid',
            'name': 'PerfTest',
            'notify_user_ids': cls.user_wa_admin.ids,
            'phone_uid': '1122334455',
            'token': 'token',
        })

        cls.test_wa_records = cls.env['whatsapp.test.base'].create([
            {
                'country_id': cls.env.ref('base.be').id,
                'customer_id': cls.customers[0].id,
                'name': 'Test Be',
            }, {
                'country_id': cls.env.ref('base.in').id,
                'customer_id': cls.customers[1].id,
                'name': 'Test In',
            }
        ])

        cls.wa_template = cls.env['whatsapp.template'].create({
            'body': ('Hello I am {{1}}, call me on {{2}}. '
                     'You are from {{3}}. Sample text {{4}}'),
            'header_type': 'text',
            'header_text': 'Header {{1}}',
            'footer_text': 'Footer',
            'model_id': cls.env['ir.model']._get_id('whatsapp.test.base'),
            'name': 'Test-perf',
            'status': 'approved',
            'variable_ids': [
                (5, 0, 0),
                # body
                (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': "user_name", 'demo_value': "Admin"}),
                (0, 0, {'name': "{{2}}", 'line_type': "body", 'field_type': "user_mobile", 'demo_value': "+32 456 00 11 22"}),
                (0, 0, {'name': "{{3}}", 'line_type': "body", 'field_type': "field", 'field_name': "country_id.name",
                        'demo_value': "CountryDemo"}),
                (0, 0, {'name': "{{4}}", 'line_type': "body", 'field_type': "free_text", 'demo_value': "BodyText"}),
                # header
                (0, 0, {'name': "{{1}}", 'line_type': "header", 'field_type': "free_text", 'demo_value': "HeaderText"}),
            ],
        })

    @users('employee')
    @warmup
    def test_composer_mono(self):
        test_wa_record = self.test_wa_records[0].with_user(self.env.user)
        wa_template = self.wa_template.with_user(self.env.user)

        with self.mockWhatsappGateway(), self.assertQueryCount(employee=29):
            composer = self.env['whatsapp.composer'].with_context({
                'active_model': test_wa_record._name,
                'active_ids': test_wa_record.ids,
            }).create({
                'wa_template_id': wa_template.id,
            })
            composer.action_send_whatsapp_template()
