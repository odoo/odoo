from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo import Command


class TestMergePartner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Bank = self.env['res.partner.bank']

        # Create partners
        self.partner1 = self.Partner.create({'name': 'Partner 1', 'email': 'partner1@example.com'})
        self.partner2 = self.Partner.create({'name': 'Partner 2', 'email': 'partner2@example.com'})
        self.partner3 = self.Partner.create({'name': 'Partner 3', 'email': 'partner3@example.com'})

        # Create bank accounts
        self.bank1 = self.Bank.create({'acc_number': '12345', 'partner_id': self.partner1.id})
        self.bank2 = self.Bank.create({'acc_number': '54321', 'partner_id': self.partner2.id})
        self.bank3 = self.Bank.create({'acc_number': '12345', 'partner_id': self.partner3.id})  # Duplicate account number

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
        self.attachment_bank1 = self.env['ir.attachment'].create({
            'name': 'Attachment Bank 1',
            'res_model': 'res.partner.bank',
            'res_id': self.bank1.id,
        })
        self.attachment_bank2 = self.env['ir.attachment'].create({
            'name': 'Attachment Bank 2',
            'res_model': 'res.partner.bank',
            'res_id': self.bank2.id,
        })
        self.attachment_bank3 = self.env['ir.attachment'].create({
            'name': 'Attachment Bank 2',
            'res_model': 'res.partner.bank',
            'res_id': self.bank3.id,
        })

    def test_merge_partners_without_bank_accounts(self):
        """ Test merging partners without any bank accounts """
        partner4 = self.Partner.create({'name': 'Partner 4', 'email': 'partner4@example.com'})
        partner5 = self.Partner.create({'name': 'Partner 5', 'email': 'partner5@example.com'})
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([partner4.id, partner5.id], partner4)
        self.assertFalse(partner5.exists(), "Source partner should be deleted after merge")
        self.assertTrue(partner4.exists(), "Destination partner should exist after merge")

    def test_merge_partners_with_unique_bank_accounts(self):
        """ Test merging partners with unique bank accounts """
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(self.partner2.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(self.bank1.partner_id, self.partner1, "Bank account should belong to destination partner")
        self.assertEqual(self.bank2.partner_id, self.partner1, "Bank account should be reassigned to destination partner")

    def test_merge_partners_with_duplicate_bank_accounts(self):
        """ Test merging partners with duplicate bank accounts among themselves """
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        src_partners = self.partner1 + self.partner3
        wizard._merge((src_partners + self.partner2).ids, self.partner2)

        self.assertFalse(src_partners.exists(), "Source partners should be deleted after merge")
        self.assertTrue(self.partner2.exists(), "Destination partner should exist after merge")
        self.assertRecordValues(self.partner2.bank_ids, [
            {'acc_number': '12345'},
            {'acc_number': '54321'},
        ])
        self.assertEqual(self.attachment_bank1.res_id, self.bank1.id, "Bank attachment should remain linked to the correct bank account")
        self.assertEqual(self.attachment_bank3.res_id, self.bank1.id, "Bank attachment should be reassigned to the correct bank account")

    def test_merge_partners_with_duplicate_bank_accounts_with_destination(self):
        """ Test merging partners with duplicate bank accounts with the destination partner """
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner3.id], self.partner1)

        self.assertFalse(self.partner3.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(len(self.partner1.bank_ids), 1, "There should be a single bank account after merge")
        self.assertIn(self.bank1, self.partner1.bank_ids, "The original bank account of the destination partner should remain")
        self.assertFalse(self.bank3.exists(), "The duplicate bank account should have been deleted.")

    def test_merge_partners_with_references(self):
        """ Test merging partners with references """
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(self.partner2.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(self.attachment1.res_id, self.partner1.id, "Attachment should be linked to the destination partner")
        self.assertEqual(self.attachment2.res_id, self.partner1.id, "Attachment should be reassigned to the destination partner")

    def test_merge_partners_with_peon_user(self):
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

        # internal user doesn't have the right to write on res.partner.bank
        with self.assertRaises(AccessError):
            self.bank1.with_user(user_peon).partner_id = self.partner2

        wizard = self.env['base.partner.merge.automatic.wizard'].with_user(user_peon).create({})
        src_partners = self.partner1 + self.partner3
        wizard._merge((src_partners + self.partner2).ids, self.partner2, extra_checks=False)

        self.assertFalse(src_partners.exists(), "Source partners should be deleted after merge")
        self.assertTrue(self.partner2.exists(), "Destination partner should exist after merge")
        self.assertRecordValues(self.partner2.bank_ids, [
            {'acc_number': '12345'},
            {'acc_number': '54321'},
        ])
        self.assertEqual(self.attachment_bank1.res_id, self.bank1.id, "Bank attachment should remain linked to the correct bank account")
        self.assertEqual(self.attachment_bank3.res_id, self.bank1.id, "Bank attachment should be reassigned to the correct bank account")
