# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestResponsiveMail(common.SavepointCase):

    def test_responsive_mail(self):
        """ Testing mail mailing responsive mail body """
        self.user_employee = self.env['res.users'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
            'no_reset_password': True,
        }).create({
            'name': 'Geraldine Mass Mailing User',
            'login': 'geraldine',
            'email': 'g.g@example.com',
            'groups_id': [(6, 0, [  
                self.env.ref('mass_mailing.group_mass_mailing_user').id,
                self.env.ref('base.group_partner_manager').id,  # TDE FIXME: check if really necessary for mass mailing
            ])],
        })

        test_record = self.env['res.partner'].create({'name': 'Mass Mail Partner'})
        mass_mail_record = self.env['mail.mass_mailing'].sudo(self.user_employee).create({
            'name': 'Test',
            'state': 'draft',
            'mailing_model_id': self.env.ref('base.model_res_partner').id,
        })

        composer = self.env['mail.compose.message'].sudo(self.user_employee).with_context({
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
