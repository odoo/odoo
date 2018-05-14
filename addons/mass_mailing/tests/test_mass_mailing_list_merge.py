# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.test_mail.tests.common import MockEmails
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE_BOUNCE


class TestMassMailingCommon(common.TransactionCase):

    def test_00_test_mass_mailing_list_merge(self):
        # Data set up

        mailing_list_A = self.env['mail.mass_mailing.list'].create({
            'name': 'A',
            'contact_ids': [
                (0, 0, {'name': 'Noel Flantier', 'email': 'noel.flantier@example.com'}),
                (0, 0, {'name': 'Gorramts', 'email': 'gorramts@example.com'}),
                (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
            ]
        })

        mailing_list_B = self.env['mail.mass_mailing.list'].create({
            'name': 'B',
            'contact_ids': [
                (0, 0, {'name': 'Icallhimtest', 'email': 'icallhimtest@example.com'}),
                (0, 0, {'name': 'Norbert', 'email': 'norbert@example.com'}),
                (0, 0, {'name': 'Ybrant_Zoulou', 'email': 'ybrant@example.com'}),
            ]
        })

        mailing_list_C = self.env['mail.mass_mailing.list'].create({
            'name': 'C',
            'contact_ids': [
                (0, 0, {'name': 'Norberto', 'email': 'norbert@example.com'}),
            ]
        })

        # TEST CASE: Merge A,B into the existing mailing list C
        # The mailing list C contains the same email address than 'Rorbert' in list B
        # This test ensure that the mailing lists are correctly merged and no
        # duplicates are appearing in C

        result_list = self.env['mass.mailing.list.merge'].create({
            'src_list_ids': [(4, list_id) for list_id in [mailing_list_A.id, mailing_list_B.id]],
            'dest_list_id': mailing_list_C.id,
            'merge_options': 'existing',
            'new_list_name': False,
            'archive_src_lists': False,
        }).action_mailing_lists_merge()

        # Assert the number of contacts is correct
        self.assertEqual(
            len(result_list.contact_ids.ids), 5,
            'The number of contacts on the mailing list C is not equal to 5')

        # Assert there's no duplicated email address
        self.assertEqual(
            len(list(set(result_list.contact_ids.mapped('email')))), 5,
            'Duplicates have been merged into the destination mailing list. Check %s' % (result_list.contact_ids.mapped('email')))


class TestMassMailing(MockEmails):

    def test_mass_mailing_bounce(self):
        MassMailingContacts = self.env['mail.mass_mailing.contact']
        MassMailing = self.env['mail.mass_mailing']

        # set bounce alias and domain to handle bounce email
        self.env['ir.config_parameter'].set_param('mail.bounce.alias', 'bounce.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'test.com')

        # create mailing contact record
        self.mailing_contact_1 = MassMailingContacts.create({'name': 'test email 1', 'email': 'test1@email.com'})

        # create mass mailing record
        self.mass_mailing = MassMailing.create({
            'name': 'test',
            'mailing_domain': [('id', 'in', [self.mailing_contact_1.id])],
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
        composer = self.env['mail.compose.message'].with_context(active_ids=res_ids, mass_mailing_seen_list=self.mass_mailing._get_seen_list()).create(composer_values)
        composer.send_mail()
        email_to = self._mails[0]['headers']['Return-Path']
        self.format_and_process(MAIL_TEMPLATE_BOUNCE, to=email_to, target_model='mail.mass_mailing')
        self.assertEqual(self.mass_mailing.bounced, 1, 'there should bounced email, should be equals to 1')
