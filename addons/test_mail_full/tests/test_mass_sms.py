# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.mass_mailing_sms.tests import common as mass_mailing_sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('mass_mailing')
class TestMassSMS(test_mail_full_common.MassSMSBaseFunctionalTest, mass_mailing_sms_common.MockSMS):

    @classmethod
    def setUpClass(cls):
        super(TestMassSMS, cls).setUpClass()
        cls._test_body = 'Mass SMS in your face'

        records = cls.env['mail.test.sms']
        partners = cls.env['res.partner']
        country_be_id = cls.env.ref('base.be').id,
        country_us_id = cls.env.ref('base.us').id,

        for x in range(10):
            partners += cls.env['res.partner'].with_context(**cls._test_context).create({
                'name': 'Partner_%s' % (x),
                'email': '_test_partner_%s@example.com' % (x),
                'country_id': country_be_id,
                'mobile': '045600%s%s99' % (x, x)
            })
            records += cls.env['mail.test.sms'].with_context(**cls._test_context).create({
                'name': 'MassSMSTest_%s' % (x),
                'customer_id': partners[x].id,
                'phone_nbr': '045600%s%s44' % (x, x)
            })
        cls.records = cls._reset_mail_context(records)
        cls.records_numbers = [phone_validation.phone_format(r.phone_nbr, 'BE', '32', force_format='E164') for r in cls.records]
        cls.partners = partners

        cls.sms_template = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is a mass SMS.',
        })

        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in partners
        ]

        cls.mailing = cls.env['mailing.mailing'].with_user(cls.user_marketing).create({
            'name': 'Xmas Spam',
            'subject': 'Xmas Spam',
            'mailing_model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'mailing_type': 'sms',
            'mailing_domain': '%s' % repr([('name', 'ilike', 'MassSMSTest')]),
            'sms_template_id': cls.sms_template.id,
            'sms_allow_unsubscribe': False,
        })

    def test_mass_sms_internals(self):
        with self.sudo('marketing'):
            mailing = self.env['mailing.mailing'].create({
                'name': 'Xmas Spam',
                'subject': 'Xmas Spam',
                'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
                'mailing_type': 'sms',
                'mailing_domain': '%s' % repr([('name', 'ilike', 'MassSMSTest')]),
                'sms_template_id': self.sms_template.id,
                'sms_allow_unsubscribe': False,
            })

            self.assertEqual(mailing.mailing_model_real, 'mail.test.sms')
            self.assertEqual(mailing.medium_id, self.env.ref('mass_mailing_sms.utm_medium_sms'))
            self.assertEqual(mailing.body_plaintext, self.sms_template.body)

            remaining_res_ids = mailing._get_remaining_recipients()
            self.assertEqual(set(remaining_res_ids), set(self.records.ids))

            with self.mockSMSGateway():
                mailing.action_send_sms()

        self.assertSMSStatistics(
            [{'partner': record.customer_id, 'number': self.records_numbers[i], 'content': 'Dear %s this is a mass SMS.' % record.display_name} for i, record in enumerate(self.records)],
            mailing, self.records, check_sms=True
        )

    def test_mass_sms_internals_errors(self):
        # same customer, specific different number on record -> should be valid
        new_record_1 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_nr1',
            'customer_id': self.partners[0].id,
            'phone_nbr': '0456999999',
        })
        # new customer, number already on record -> should be ignored
        country_be_id = self.env.ref('base.be').id,
        nr2_partner = self.env['res.partner'].create({
            'name': 'Partner_nr2',
            'country_id': country_be_id,
            'mobile': '0456449999',
        })
        new_record_2 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_nr2',
            'customer_id': nr2_partner.id,
            'phone_nbr': self.records[0].phone_nbr,
        })
        records_numbers = self.records_numbers + ['+32456999999']

        with self.sudo('marketing'):
            with self.mockSMSGateway():
                self.mailing.action_send_sms()

        self.assertSMSStatistics(
            [{'partner': record.customer_id, 'number': records_numbers[i], 'content': 'Dear %s this is a mass SMS.' % record.display_name} for i, record in enumerate(self.records | new_record_1)],
            self.mailing, self.records | new_record_1, check_sms=True
        )
        self.assertSMSStatistics(
            [{'partner': new_record_2.customer_id, 'number': self.records_numbers[0], 'content': 'Dear %s this is a mass SMS.' % new_record_2.display_name, 'state': 'ignored', 'failure_type': 'sms_duplicate'}],
            self.mailing, new_record_2, check_sms=True
        )

    def test_mass_sms_internals_done_ids(self):
        with self.sudo('marketing'):
            with self.mockSMSGateway():
                self.mailing.action_send_sms(res_ids=self.records[:5].ids)

        traces = self.env['mailing.trace'].search([('mass_mailing_id', 'in', self.mailing.ids)])
        self.assertEqual(len(traces), 5)
        # new traces generated
        self.assertSMSStatistics(
            [{'partner': record.customer_id, 'number': self.records_numbers[i], 'content': 'Dear %s this is a mass SMS.' % record.display_name} for i, record in enumerate(self.records[:5])],
            self.mailing, self.records[:5], check_sms=True
        )

        with self.sudo('marketing'):
            with self.mockSMSGateway():
                self.mailing.action_send_sms(res_ids=self.records.ids)

        # delete old traces (for testing purpose: ease check by deleting old ones)
        traces.unlink()
        # new failed traces generated for duplicates
        self.assertSMSStatistics(
            [{'partner': record.customer_id, 'number': self.records_numbers[i], 'content': 'Dear %s this is a mass SMS.' % record.display_name, 'state': 'ignored', 'failure_type': 'sms_duplicate'} for i, record in enumerate(self.records[:5])],
            self.mailing, self.records[:5], check_sms=True
        )
        # new traces generated
        self.assertSMSStatistics(
            [{'partner': record.customer_id, 'number': self.records_numbers[i+5], 'content': 'Dear %s this is a mass SMS.' % record.display_name} for i, record in enumerate(self.records[5:])],
            self.mailing, self.records[5:], check_sms=True
        )
