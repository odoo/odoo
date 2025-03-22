# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.tests.common import users


class TestMassMailValues(MassSMSCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailValues, cls).setUpClass()

        cls._create_mailing_list()
        cls.sms_template_partner = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get('res.partner').id,
            'body': 'Dear {{ object.display_name }} this is an SMS.'
        })

    @users('user_marketing')
    def test_mailing_computed_fields(self):
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'sms',
            'body_plaintext': 'Coucou hibou',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(mailing.user_id, self.user_marketing)
        self.assertEqual(mailing.body_plaintext, 'Coucou hibou')
        self.assertEqual(mailing.medium_id, self.env.ref('mass_mailing_sms.utm_medium_sms'))
        self.assertEqual(mailing.mailing_model_name, 'res.partner')
        self.assertEqual(mailing.mailing_model_real, 'res.partner')
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('phone_sanitized_blacklisted', '=', False)])
        # update template -> update body
        mailing.write({'sms_template_id': self.sms_template_partner.id})
        self.assertEqual(mailing.body_plaintext, self.sms_template_partner.body)
        # update domain
        mailing.write({
            'mailing_domain': [('email', 'ilike', 'test.example.com')]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

        # reset mailing model -> reset domain; set reply_to -> keep it
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(mailing.mailing_model_name, 'mailing.list')
        self.assertEqual(mailing.mailing_model_real, 'mailing.contact')
        # default for mailing list: depends upon contact_list_ids
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', [])])
        mailing.write({
            'contact_list_ids': [(4, self.mailing_list_1.id), (4, self.mailing_list_2.id)]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', (self.mailing_list_1 | self.mailing_list_2).ids)])

    @users('user_marketing')
    def test_mailing_get_sms_link_replacements_placeholders(self):
        """Test the extra chars counts for estimating total SMS characters length.

          * links are transformed into "[base_url]/r/[link_tracker_code]/s/[sms_id]".
          * opt-out link is formatted as "\nSTOP SMS : [base_url]/sms/[mailing_id]/[trace_code]".
        See `get_sms_link_replacements_placeholders` for safety characters.
        """
        mailing = self.env['mailing.mailing'].create({
            'body_plaintext': 'Coucou hibou',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_type': 'sms',
            'name': 'TestMailing',
            'subject': 'Test',
        })
        base_url = self.env['mailing.mailing'].get_base_url()

        link_trackers = bool(self.env['link.tracker'].search([], limit=1))  # depends on demo

        expected = {
            'link': f'{base_url}/r/xxx{"x" if link_trackers else ""}/s/xxxxx',
            'unsubscribe': f"\nSTOP SMS : {base_url}/sms/{'x' * len(str(mailing.id))}/{'x' * self.env['mailing.trace'].CODE_SIZE}",
        }
        self.assertDictEqual(mailing.get_sms_link_replacements_placeholders(), expected)

        no_mailing = self.env['mailing.mailing']
        self.assertDictEqual(no_mailing.get_sms_link_replacements_placeholders(), expected)

        new_mailing = self.env['mailing.mailing'].new()
        self.assertDictEqual(new_mailing.get_sms_link_replacements_placeholders(), expected)
