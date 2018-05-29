# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMassMailOnLead(common.TransactionCase):

    def test_mass_mail_on_lead(self):
        Lead = self.env['crm.lead']
        MassMailing = self.env['mail.mass_mailing']

        # create mailing contact record
        lead_a = Lead.create({
            'name': 'test email 1',
            'email_from': 'test1@email.com',
            'opt_out': True,
        })
        lead_b = Lead.create({
            'name': 'test email 2',
            'email_from': 'test2@email.com',
        })
        lead_c = Lead.create({
            'name': 'test email 3',
            'email_from': 'test3@email.com',
        })

        # Set Blacklist
        self.blacklist_contact_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'test2@email.com',
        })

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'One',
            'mailing_domain': [('id', 'in', [lead_a.id, lead_b.id, lead_c.id])],
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.mailing_model_real = 'crm.lead'
        self.mass_mailing.put_in_queue()
        res_ids = self.mass_mailing.get_remaining_recipients()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(
            active_ids=res_ids,
            mass_mailing_seen_list=self.mass_mailing._get_seen_list(),
            mass_mailing_unsubscribed_list=self.mass_mailing._get_unsubscribed_list()).create(composer_values)
        composer.send_mail()
        # if user is opt_out on One list but not on another, send the mail anyway
        self.assertEqual(self.mass_mailing.ignored, 2,
            'Opt Out ignored email number incorrect, should be equals to 2')