# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common


class TestAccessRights(common.TransactionCase):

    def test_01_mass_mail_blacklist(self):
        MassMailingContacts = self.env['mail.mass_mailing.contact']
        MassMailing = self.env['mail.mass_mailing']
        MailBlacklist = self.env['mail.mass_mailing.blacklist']

        # create mailing contact record
        self.mailing_contact_1 = MassMailingContacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        self.mailing_contact_2 = MassMailingContacts.create({'name': 'test email 2', 'email': 'test2@email.com'})
        self.mailing_contact_3 = MassMailingContacts.create({'name': 'test email 3', 'email': 'test3@email.com'})
        self.mailing_contact_4 = MassMailingContacts.create({'name': 'test email 4', 'email': 'test4@email.com'})
        self.mailing_contact_5 = MassMailingContacts.create({'name': 'test email 5', 'email': 'test5@email.com'})

        # create blacklist record
        MailBlacklist.create({'name': self.mailing_contact_3.name, 'email': self.mailing_contact_3.email})
        MailBlacklist.create({'name': self.mailing_contact_4.name, 'email': self.mailing_contact_4.email})

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'test',
            'mailing_domain': [('id', 'in',
                                [self.mailing_contact_1.id, self.mailing_contact_2.id, self.mailing_contact_3.id,
                                 self.mailing_contact_4.id, self.mailing_contact_5.id])],
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
        composer = self.env['mail.compose.message'].with_context(active_ids=res_ids,
                                                                 mass_mailing_seen_list=self.mass_mailing._get_seen_list()).create(
            composer_values)
        composer.send_mail()
        self.assertEqual(self.mass_mailing.ignored, 2, 'blacklist ignored email number incorrect, should be equals to 2')

    def test_02_mass_mail_simple_opt_out(self):
        MassMailingContacts = self.env['mail.mass_mailing.contact']
        MassMailingLists = self.env['mail.mass_mailing.list']
        MassMailingOptOut = self.env['mail.mass_mailing.list_contact_rel']
        MassMailing = self.env['mail.mass_mailing']

        # create mailing contact record
        mailing_contact_1 = MassMailingContacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        mailing_contact_2 = MassMailingContacts.create({'name': 'test email 2', 'email': 'test2@email.com'})

        # create mailing list record
        mailing_list_1 = MassMailingLists.create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })

        # Set Opt out
        MassMailingOptOut.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({
            'opt_out': True,
        })

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'One',
            'mailing_model_id': self.env['ir.model']._get(MassMailingContacts).id,
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.contact_list_ids = [mailing_list_1.id]
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
        self.assertEqual(self.mass_mailing.ignored, 1,
            'Opt Out ignored email number incorrect, should be equals to 1')


    def test_03_mass_mail_multi_opt_out(self):
        MassMailingContacts = self.env['mail.mass_mailing.contact']
        MassMailingLists = self.env['mail.mass_mailing.list']
        MassMailingOptOut = self.env['mail.mass_mailing.list_contact_rel']
        MassMailing = self.env['mail.mass_mailing']

        # create mailing contact record
        mailing_contact_1 = MassMailingContacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        mailing_contact_2 = MassMailingContacts.create({'name': 'test email 2', 'email': 'test2@email.com'})

        # create mailing list record
        mailing_list_1 = MassMailingLists.create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })
        mailing_list_2 = MassMailingLists.create({
            'name': 'B',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })

        # Set Opt out
        MassMailingOptOut.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({
            'opt_out': True,
        })

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'One',
            'mailing_model_id': self.env['ir.model']._get(MassMailingContacts).id,
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.contact_list_ids = [mailing_list_1.id, mailing_list_2.id]
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
        self.assertEqual(self.mass_mailing.ignored, 0,
            'Opt Out ignored email number incorrect, should be equals to 0')

    def test_mass_mail_on_res_partner(self):
        Partners = self.env['res.partner']
        MassMailing = self.env['mail.mass_mailing']

        # create mailing contact record
        partner_a = Partners.create({
            'name': 'test email 1',
            'email': 'test1@email.com',
            'opt_out': True,
        })
        partner_b = Partners.create({
            'name': 'test email 2',
            'email': 'test2@email.com',
        })
        partner_c = Partners.create({
            'name': 'test email 3',
            'email': 'test3@email.com',
        })

        # Set Blacklist
        self.blacklist_contact_entry = self.env['mail.mass_mailing.blacklist'].create({
            'email': 'test2@email.com',
        })

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'One',
            'mailing_domain': [('id', 'in', [partner_a.id, partner_b.id, partner_c.id])],
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.mailing_model_real = 'res.partner'
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