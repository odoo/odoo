# -*- coding: utf-8 -*-

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail.tests.common import mail_new_test_user


class BaseFunctionalTest(test_mail_common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls.user_employee.write({'login': 'employee'})

        # update country to belgium in order to test sanitization of numbers
        cls.user_employee.company_id.write({'country_id': cls.env.ref('base.be').id})

        # some numbers for testing
        cls.random_numbers_str = '+32456998877, 0456665544'
        cls.random_numbers = cls.random_numbers_str.split(', ')
        cls.random_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.random_numbers]
        cls.test_numbers = ['+32456010203', '0456 04 05 06', '0032456070809']
        cls.test_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.test_numbers]

        # some numbers for mass testing
        cls.mass_numbers = ['04561%s2%s3%s' % (x, x, x) for x in range(0, 10)]
        cls.mass_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.mass_numbers]

    @classmethod
    def _create_sms_template(cls, model, body=False):
        return cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get(model).id,
            'body': body if body else 'Dear ${object.display_name} this is an SMS.'
        })

    @classmethod
    def _create_records_for_batch(cls, model, count):
        records = cls.env['mail.test.sms']
        partners = cls.env['res.partner']
        country_id = cls.env.ref('base.be').id,
        for x in range(count):
            partners += cls.env['res.partner'].with_context(**cls._test_context).create({
                'name': 'Partner_%s' % (x),
                'email': '_test_partner_%s@example.com' % (x),
                'country_id': country_id,
                'mobile': '047500%02d%02d' % (x, x)
            })
            records += cls.env[model].with_context(**cls._test_context).create({
                'name': 'Test_%s' % (x),
                'customer_id': partners[x].id,
            })
        cls.records = cls._reset_mail_context(records)
        cls.partners = partners


class TestRecipients(test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestRecipients, cls).setUpClass()
        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]


class MassSMSBaseFunctionalTest(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(MassSMSBaseFunctionalTest, cls).setUpClass()
        cls.user_marketing = mail_new_test_user(
            cls.env, login='marketing',
            groups='base.group_user,mass_mailing.group_mass_mailing_user',
            name='Martial Marketing', signature='--\nMartial')
