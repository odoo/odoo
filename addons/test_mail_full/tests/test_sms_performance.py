# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance')
class TestSMSPerformance(BaseMailPerformance, sms_common.SMSCase):

    def setUp(self):
        super(TestSMSPerformance, self).setUp()
        self.user_employee.write({
            'login': 'employee',
            'country_id': self.env.ref('base.be').id,
        })
        self.admin = self.env.user

        self.customer = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Test Customer',
            'email': 'test@example.com',
            'mobile': '0456123456',
            'country_id': self.env.ref('base.be').id,
        })
        self.test_record = self.env['mail.test.sms'].with_context(self._quick_create_ctx).create({
            'name': 'Test',
            'customer_id': self.customer.id,
            'phone_nbr': '0456999999',
        })

        # prepare recipients to test for more realistic workload
        Partners = self.env['res.partner'].with_context(self._quick_create_ctx)
        self.partners = self.env['res.partner']
        for x in range(0, 10):
            self.partners |= Partners.create({
                'name': 'Test %s' % x,
                'email': 'test%s@example.com' % x,
                'mobile': '0456%s%s0000' % (x, x),
                'country_id': self.env.ref('base.be').id,
            })

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

    @mute_logger('odoo.addons.sms.models.sms_sms')
    @users('employee')
    @warmup
    def test_message_sms_record_1_partner(self):
        record = self.test_record.with_user(self.env.user)
        pids = self.customer.ids
        with self.mockSMSGateway(sms_allow_unlink=True), self.assertQueryCount(employee=23):  # test_mail_enterprise: 25
            messages = record._message_sms(
                body='Performance Test',
                partner_ids=pids,
            )

        self.assertEqual(record.message_ids[0].body, '<p>Performance Test</p>')
        self.assertSMSNotification([{'partner': self.customer}], 'Performance Test', messages, sent_unlink=True)

    @mute_logger('odoo.addons.sms.models.sms_sms')
    @users('employee')
    @warmup
    def test_message_sms_record_10_partners(self):
        record = self.test_record.with_user(self.env.user)
        pids = self.partners.ids
        with self.mockSMSGateway(sms_allow_unlink=True), self.assertQueryCount(employee=41):  # test_mail_enterprise: 43
            messages = record._message_sms(
                body='Performance Test',
                partner_ids=pids,
            )

        self.assertEqual(record.message_ids[0].body, '<p>Performance Test</p>')
        self.assertSMSNotification([{'partner': partner} for partner in self.partners], 'Performance Test', messages, sent_unlink=True)

    @mute_logger('odoo.addons.sms.models.sms_sms')
    @users('employee')
    @warmup
    def test_message_sms_record_default(self):
        record = self.test_record.with_user(self.env.user)
        with self.mockSMSGateway(sms_allow_unlink=True), self.assertQueryCount(employee=26):  # test_mail_enterprise: 28
            messages = record._message_sms(
                body='Performance Test',
            )

        self.assertEqual(record.message_ids[0].body, '<p>Performance Test</p>')
        self.assertSMSNotification([{'partner': self.customer}], 'Performance Test', messages, sent_unlink=True)


@tagged('mail_performance')
class TestSMSMassPerformance(BaseMailPerformance, sms_common.MockSMS):

    def setUp(self):
        super(TestSMSMassPerformance, self).setUp()
        be_country_id = self.env.ref('base.be').id,
        self.user_employee.write({
            'login': 'employee',
            'country_id': be_country_id,
        })
        self.admin = self.env.user
        self.admin.write({
            'country_id': be_country_id,
        })

        self._test_body = 'MASS SMS'

        records = self.env['mail.test.sms']
        partners = self.env['res.partner']
        for x in range(50):
            partners += self.env['res.partner'].with_context(**self._quick_create_ctx).create({
                'name': 'Partner_%s' % (x),
                'email': '_test_partner_%s@example.com' % (x),
                'country_id': be_country_id,
                'mobile': '047500%02d%02d' % (x, x)
            })
            records += self.env['mail.test.sms'].with_context(**self._quick_create_ctx).create({
                'name': 'Test_%s' % (x),
                'customer_id': partners[x].id,
            })
        self.partners = partners
        self.records = records

        self.sms_template = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.',
        })

    @mute_logger('odoo.addons.sms.models.sms_sms')
    @users('employee')
    @warmup
    def test_composer_mass_active_domain(self):
        composer = self.env['sms.composer'].with_context(
            default_composition_mode='mass',
            default_res_model='mail.test.sms',
            default_use_active_domain=True,
            active_domain=[('id', 'in', self.records.ids)],
        ).create({
            'body': self._test_body,
            'mass_keep_log': False,
        })

        with self.mockSMSGateway(sms_allow_unlink=True), self.assertQueryCount(employee=106):
                composer.action_send_sms()

    @mute_logger('odoo.addons.sms.models.sms_sms')
    @users('employee')
    @warmup
    def test_composer_mass_active_domain_w_log(self):
        composer = self.env['sms.composer'].with_context(
            default_composition_mode='mass',
            default_res_model='mail.test.sms',
            default_use_active_domain=True,
            active_domain=[('id', 'in', self.records.ids)],
        ).create({
            'body': self._test_body,
            'mass_keep_log': True,
        })

        with self.mockSMSGateway(sms_allow_unlink=True), self.assertQueryCount(employee=157):
            composer.action_send_sms()
