# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import users


class TestMailingListMerge(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailingListMerge, cls).setUpClass()
        cls._create_mailing_list()

        cls.mailing_list_3 = cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'ListC',
            'contact_ids': [
                (0, 0, {'name': 'Norberto', 'email': 'norbert@example.com'}),
            ]
        })

    @users('user_marketing')
    def test_mailing_list_merge(self):
        # TEST CASE: Merge A,B into the existing mailing list C
        # The mailing list C contains the same email address than 'Norbert' in list B
        # This test ensure that the mailing lists are correctly merged and no
        # duplicates are appearing in C

        result_list = self.env['mailing.list.merge'].create({
            'src_list_ids': [(4, list_id) for list_id in [self.mailing_list_1.id, self.mailing_list_2.id]],
            'dest_list_id': self.mailing_list_3.id,
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
