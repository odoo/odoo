# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import tools
from odoo.tests import common


class TestAutoBlacklist(common.TransactionCase):

    def test_mail_bounced_auto_blacklist(self):
        mass_mailing_contacts = self.env['mailing.contact']
        mass_mailing = self.env['mailing.mailing']
        mail_blacklist = self.env['mail.blacklist']
        mail_statistics = self.env['mailing.trace']

        # create mailing contact record
        self.mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email 1', 'email': 'Test1@email.com'})

        base_parsed_values = {
            'email_from': 'toto@yaourth.com', 'to': 'tata@yaourth.com', 'message_id': '<123.321@yaourth.com>',
            'bounced_partner': self.env['res.partner'].sudo(), 'bounced_message': self.env['mail.message'].sudo()
        }

        # create bounced history of 4 statistics
        for idx in range(4):
            mail_statistics.create({
                'model': 'mailing.contact',
                'res_id': self.mailing_contact_1.id,
                'bounced': datetime.datetime.now() - datetime.timedelta(weeks=idx+2),
                'email': self.mailing_contact_1.email,
                'message_id': '<123.00%s@iron.sky>' % idx,
            })
            base_parsed_values.update({
                'bounced_email': tools.email_normalize(self.mailing_contact_1.email),
                'bounced_msg_id': '<123.00%s@iron.sky>' % idx
            })
            self.env['mail.thread']._routing_handle_bounce(False, base_parsed_values)

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'test',
            'subject': 'Booooounce!',
            'mailing_domain': [('id', 'in',
                                [self.mailing_contact_1.id])],
            'body_html': 'This is a bounced mail for auto blacklist demo'})
        self.mass_mailing.action_put_in_queue()
        res_ids = self.mass_mailing._get_remaining_recipients()
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
            mass_mailing_seen_list=self.mass_mailing._get_seen_list()
        ).create(composer_values)
        composer.send_mail()

        mail_statistics.create({
            'model': 'mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now(),
            'email': self.mailing_contact_1.email,
            'message_id': '<123.004@iron.sky>',
        })
        base_parsed_values.update({
            'bounced_email': tools.email_normalize(self.mailing_contact_1.email),
            'bounced_msg_id': '<123.004@iron.sky>'
        })
        # call bounced
        self.env['mail.thread']._routing_handle_bounce(False, base_parsed_values)

        # check blacklist
        blacklist_record = mail_blacklist.search([('email', '=', self.mailing_contact_1.email)])
        self.assertEqual(len(blacklist_record), 1,
                         'The email %s must be blacklisted' % self.mailing_contact_1.email)
