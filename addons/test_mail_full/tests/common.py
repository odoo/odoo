# -*- coding: utf-8 -*-

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon


class TestMailFullCommon(TestMassMailCommon, MassSMSCommon):

    @classmethod
    def _create_records_for_batch(cls, model, count):
        records = cls.env[model]
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


class TestRecipients(TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestRecipients, cls).setUpClass()
        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]
