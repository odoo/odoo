# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import TestMail


class test_message_compose(TestMail):

    def test_OO_mail_mail_tracking(self):
        """ Tests designed for mail_mail tracking (opened, replied, bounced) """
        pass

    def test_01_mass_mail_blacklist(self):
        MassMailingContacts = self.env['mail.mass_mailing.contact']
        MassMailing = self.env['mail.mass_mailing']
        MailBlacklist = self.env['mail.blacklist']

        # create mailing contact record
        self.mailing_contact_1 = MassMailingContacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        self.mailing_contact_2 = MassMailingContacts.create({'name': 'test email 2', 'email': 'test2@email.com'})
        self.mailing_contact_3 = MassMailingContacts.create({'name': 'test email 3', 'email': 'test3@email.com'})
        self.mailing_contact_4 = MassMailingContacts.create({'name': 'test email 4', 'email': 'test4@email.com'})
        self.mailing_contact_5 = MassMailingContacts.create({'name': 'test email 5', 'email': 'test5@email.com'})

        # create blacklist record
        MailBlacklist.create({'email': self.mailing_contact_3.email})
        MailBlacklist.create({'email': self.mailing_contact_4.email})

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'test',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': [('id', 'in', [self.mailing_contact_1.id, self.mailing_contact_2.id, self.mailing_contact_3.id, self.mailing_contact_4.id, self.mailing_contact_5.id ])],
            'body_html': 'This is mass mail marketing demo'})
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
        composer = self.env['mail.compose.message'].with_context(active_ids=res_ids, mass_mailing_blacklist=self.mass_mailing._get_blacklist(), mass_mailing_seen_list=self.mass_mailing._get_seen_list()).create(composer_values)
        composer.send_mail()
        self.assertEqual(self.mass_mailing.failed, 2, 'blacklist failed email number incorrect, should be equals to 2')
