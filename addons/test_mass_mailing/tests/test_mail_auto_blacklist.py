# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
import datetime

class TestAutoBlacklist(common.TransactionCase):

    def test_mail_bounced_auto_blacklist(self):
        mass_mailing_contacts = self.env['mail.mass_mailing.contact']
        mass_mailing = self.env['mail.mass_mailing']
        mail_blacklist = self.env['mail.blacklist']
        mail_statistics = self.env['mail.mail.statistics']
        mail_thread = self.env['mail.thread']

        # create mailing contact record
        self.mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email 1', 'email': 'Test1@email.com'})

        # create bounced history
        mail_statistics.create({
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now() - datetime.timedelta(weeks=2),
            'email': self.mailing_contact_1.email
        })
        self.mailing_contact_1.message_receive_bounce(self.mailing_contact_1.email, self.mailing_contact_1)
        mail_statistics.create({
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now() - datetime.timedelta(weeks=3),
            'email': self.mailing_contact_1.email
        })
        self.mailing_contact_1.message_receive_bounce(self.mailing_contact_1.email, self.mailing_contact_1)
        mail_statistics.create({
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now() - datetime.timedelta(weeks=4),
            'email': self.mailing_contact_1.email
        })
        self.mailing_contact_1.message_receive_bounce(self.mailing_contact_1.email, self.mailing_contact_1)
        mail_statistics.create({
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now() - datetime.timedelta(weeks=5),
            'email': self.mailing_contact_1.email
        })
        self.mailing_contact_1.message_receive_bounce(self.mailing_contact_1.email, self.mailing_contact_1)


        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'test',
            'mailing_domain': [('id', 'in',
                                [self.mailing_contact_1.id])],
            'body_html': 'This is a bounced mail for auto blacklist demo'})
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
            mass_mailing_seen_list=self.mass_mailing._get_seen_list()
        ).create(composer_values)
        composer.send_mail()

        mail_statistics.create({
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mailing_contact_1.id,
            'bounced': datetime.datetime.now(),
            'email': self.mailing_contact_1.email
        })
        # call bounced
        self.mailing_contact_1.message_receive_bounce(self.mailing_contact_1.email, self.mailing_contact_1)

        # check blacklist
        blacklist_record = mail_blacklist.search([('email', '=', self.mailing_contact_1.email)])
        self.assertEqual(len(blacklist_record), 1,
                         'The email %s must be blacklisted' % self.mailing_contact_1.email)
