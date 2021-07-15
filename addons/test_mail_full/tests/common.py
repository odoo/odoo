# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon


class TestMailFullCommon(TestMassMailCommon, MassSMSCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailFullCommon, cls).setUpClass()

        cls.mailing_sms = cls.env['mailing.mailing'].with_user(cls.user_marketing).create({
            'name': 'XMas SMS',
            'subject': 'Xmas SMS for {object.name}',
            'mailing_model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'mailing_type': 'sms',
            'mailing_domain': '%s' % repr([('name', 'ilike', 'SMSTest')]),
            'body_plaintext': 'Dear ${object.display_name} this is a mass SMS with two links http://www.odoo.com/smstest and http://www.odoo.com/smstest/${object.id}',
            'sms_force_send': True,
            'sms_allow_unsubscribe': True,
        })

    @classmethod
    def _create_mailing_sms_test_records(cls, model='mail.test.sms', partners=None, count=1):
        """ Helper to create data. Currently simple, to be improved. """
        Model = cls.env[model]
        phone_field = 'phone_nbr' if 'phone_nbr' in Model else 'phone'
        partner_field = 'customer_id' if 'customer_id' in Model else 'partner_id'

        vals_list = []
        for idx in range(count):
            vals = {
                'name': 'SMSTestRecord_%02d' % idx,
                phone_field: '045600%02d%02d' % (idx, idx)
            }
            if partners:
                vals[partner_field] = partners[idx % len(partners)]

            vals_list.append(vals)

        return cls.env[model].create(vals_list)


class TestRecipients(TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestRecipients, cls).setUpClass()
        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]
