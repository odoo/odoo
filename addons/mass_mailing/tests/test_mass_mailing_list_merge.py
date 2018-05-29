# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMassMailingCommon(common.TransactionCase):

    def test_00_test_mass_mailing_list_merge(self):
        # Data set up

        contact_a = self.env['mail.mass_mailing.contact'].create(
            {'name': 'Noel Flantier', 'email': 'noel.flantier@example.com'})
        contact_b = self.env['mail.mass_mailing.contact'].create(
            {'name': 'Gorramts', 'email': 'gorramts@example.com'})
        contact_c = self.env['mail.mass_mailing.contact'].create(
            {'name': 'Ybrant', 'email': 'ybrant@example.com'})
        contact_d = self.env['mail.mass_mailing.contact'].create(
            {'name': 'Icallhimtest', 'email': 'icallhimtest@example.com'})
        contact_e = self.env['mail.mass_mailing.contact'].create(
            {'name': 'Norbert', 'email': 'norbert@example.com'})


        mailing_list_A = self.env['mail.mass_mailing.list'].create({
            'name': 'A',
            'contact_ids': [
                (4, contact_a.id),
                (4, contact_b.id),
                (4, contact_c.id),
            ]
        })

        mailing_list_B = self.env['mail.mass_mailing.list'].create({
            'name': 'B',
            'contact_ids': [
                (4, contact_d.id),
                (4, contact_e.id),
                (4, contact_c.id),
            ]
        })

        mailing_list_C = self.env['mail.mass_mailing.list'].create({
            'name': 'C',
            'contact_ids': [
                (4, contact_e.id),
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