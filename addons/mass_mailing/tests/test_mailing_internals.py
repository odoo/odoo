# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo.addons.mass_mailing.tests.common import TestMassMailCommon
from odoo.tests.common import users, Form


class TestMassMailValues(TestMassMailCommon):

    @users('user_marketing')
    def test_mailing_computed_fields(self):
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(mailing.user_id, self.user_marketing)
        self.assertEqual(mailing.medium_id, self.env.ref('utm.utm_medium_email'))
        self.assertEqual(mailing.mailing_model_name, 'res.partner')
        self.assertEqual(mailing.mailing_model_real, 'res.partner')
        self.assertEqual(mailing.reply_to_mode, 'email')
        self.assertEqual(mailing.reply_to, self.user_marketing.email_formatted)
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('is_blacklisted', '=', False)])
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
        self.assertEqual(mailing.reply_to_mode, 'email')
        self.assertEqual(mailing.reply_to, self.email_reply_to)
        # default for mailing list: depends upon contact_list_ids
        self.assertEqual(literal_eval(mailing.mailing_domain), [])
        mailing.write({
            'contact_list_ids': [(4, self.mailing_list_1.id), (4, self.mailing_list_2.id)]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', (self.mailing_list_1 | self.mailing_list_2).ids)])

        # reset mailing model -> reset domain and reply to mode
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mail.channel').id,
        })
        self.assertEqual(mailing.mailing_model_name, 'mail.channel')
        self.assertEqual(mailing.mailing_model_real, 'mail.channel')
        self.assertEqual(mailing.reply_to_mode, 'thread')
        self.assertFalse(mailing.reply_to)

    @users('user_marketing')
    def test_mailing_computed_fields_default(self):
        mailing = self.env['mailing.mailing'].with_context(
            default_mailing_domain=repr([('email', 'ilike', 'test.example.com')])
        ).create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

    @users('user_marketing')
    def test_mailing_computed_fields_form(self):
        mailing_form = Form(self.env['mailing.mailing'].with_context(
            default_mailing_domain="[('email', 'ilike', 'test.example.com')]",
            default_mailing_model_id=self.env['ir.model']._get('res.partner').id,
        ))
        self.assertEqual(
            literal_eval(mailing_form.mailing_domain),
            ['&', ('is_blacklisted', '=', False), ('email', 'ilike', 'test.example.com')]
        )
        self.assertEqual(mailing_form.mailing_model_real, 'res.partner')
