from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import AccessError
from odoo import Command


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMergePartner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']

        # Create partners
        self.partner1 = self.Partner.create({'name': 'Partner 1', 'email': 'partner1@example.com'})
        self.partner2 = self.Partner.create({'name': 'Partner 2', 'email': 'partner2@example.com'})
        self.partner3 = self.Partner.create({'name': 'Partner 3', 'email': 'partner3@example.com'})

        # Create references
        self.attachment1 = self.env['ir.attachment'].create({
            'name': 'Attachment 1',
            'res_model': 'res.partner',
            'res_id': self.partner1.id,
        })
        self.attachment2 = self.env['ir.attachment'].create({
            'name': 'Attachment 2',
            'res_model': 'res.partner',
            'res_id': self.partner2.id,
        })

    def test_merge_partners_without_bank_accounts(self):
        """ Test merging partners without any bank accounts """
        partner4 = self.Partner.create({'name': 'Partner 4', 'email': 'partner4@example.com'})
        partner5 = self.Partner.create({'name': 'Partner 5', 'email': 'partner5@example.com'})
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([partner4.id, partner5.id], partner4)
        self.assertFalse(partner5.exists(), "Source partner should be deleted after merge")
        self.assertTrue(partner4.exists(), "Destination partner should exist after merge")

    def test_merge_partners_with_references(self):
        """ Test merging partners with references """
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(self.partner2.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(self.attachment1.res_id, self.partner1.id, "Attachment should be linked to the destination partner")
        self.assertEqual(self.attachment2.res_id, self.partner1.id, "Attachment should be reassigned to the destination partner")

    def test_merge_partners_with_peon_user_without_bank_accounts(self):
        """ Test merging partners with a user having the bare minimum access rights"""
        self.env["ir.model.access"].create({
            'name': 'peon.access.merge.wizard',
            'group_id': self.env.ref('base.group_user').id,
            'model_id': self.env.ref('base.model_base_partner_merge_automatic_wizard').id,
            'perm_read': 1,
            'perm_write': 1,
            'perm_create': 1,
            })
        self.env["ir.model.access"].create({
            'name': 'peon.access.merge.wizard.line',
            'group_id': self.env.ref('base.group_user').id,
            'model_id': self.env.ref('base.model_base_partner_merge_line').id,
            'perm_read': 1,
            'perm_write': 1,
            'perm_create': 1,
            })
        partner_peon = self.env['res.partner'].create({
                'name': 'Peon',
                'email': 'mark.peon@example.com',
            })
        user_peon = self.env['res.users'].create({
                'login': 'peon',
                'password': 'peon',
                'partner_id': partner_peon.id,
                'group_ids': [Command.set([self.env.ref('base.group_user').id])],
            })

        wizard = self.env['base.partner.merge.automatic.wizard'].with_user(user_peon).create({})
        src_partners = self.partner1 + self.partner3
        wizard._merge((src_partners + self.partner2).ids, self.partner2, extra_checks=False)

        self.assertFalse(src_partners.exists(), "Source partners should be deleted after merge")
        self.assertTrue(self.partner2.exists(), "Destination partner should exist after merge")
