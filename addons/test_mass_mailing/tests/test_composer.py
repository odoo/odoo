# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestComposer(common.SavepointCase):

    def test_body_responsive(self):
        """ Testing mail mailing responsive mail body """
        test_user = mail_new_test_user(
            self.env, login='geraldine',
            groups='mass_mailing.group_mass_mailing_user,base.group_partner_manager'  # TDE FIXME: check if really necessary for mass mailing
        )

        test_record = self.env['res.partner'].create({'name': 'Mass Mail Partner'})
        mass_mail_record = self.env['mail.mass_mailing'].sudo(test_user).create({
            'name': 'Test',
            'state': 'draft',
            'mailing_model_id': self.env.ref('base.model_res_partner').id,
        })

        composer = self.env['mail.compose.message'].sudo(test_user).with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'res.partner',
            'default_res_id': test_record.id,
        }).create({
            'subject': 'Mass Mail Responsive',
            'body': 'I am Responsive body',
            'mass_mailing_id': mass_mail_record.id
        })

        mail_values = composer.get_mail_values([test_record.id])
        body_html = str(mail_values[test_record.id]['body_html'])

        self.assertIn('<!DOCTYPE html>', body_html)
        self.assertIn('<head>', body_html)
        self.assertIn('viewport', body_html)
        self.assertIn('@media', body_html)
        self.assertIn('I am Responsive body', body_html)
