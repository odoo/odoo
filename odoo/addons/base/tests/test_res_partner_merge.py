from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user


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

    def test_merge_portal_users_other_company(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Company B'})

        user = new_test_user(
            self.env, login='contact_merger',
            groups='base.group_user,base.group_partner_manager',
            company_id=company_a.id,
            company_ids=[Command.set((company_a + company_b).ids)],
        )

        partners = self.partner1 + self.partner2
        partners.write({'email': 'merge@example.com', 'company_id': False})
        portal_users = self.env['res.users'].create([
            {
                'login': partner.name,
                'partner_id': partner.id,
                'groups_id': [Command.set([self.env.ref('base.group_portal').id])],
                'company_id': company_a.id,
                'company_ids': [Command.set(company_a.ids)],
            }
            for partner in partners
        ])
        self.assertFalse(partners.company_id)

        for company in (company_a, company_b):
            with self.subTest(company=company.name), self.cr.savepoint():
                # Cached user relations can hide the effect of company record rules.
                self.env.invalidate_all()

                wizard = self.env['base.partner.merge.automatic.wizard'].with_user(user).with_context(
                    allowed_company_ids=company.ids,
                    active_model='res.partner', active_ids=partners.ids,
                ).create({'dst_partner_id': partners[1].id})

                with self.assertRaisesRegex(UserError, 'You cannot merge contacts linked to more than one user'):
                    wizard.action_merge()

                self.assertEqual(partners.exists(), partners)
                self.assertEqual(portal_users.mapped('partner_id'), partners)

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

    def test_merge_recomputes_source_dependents(self):
        destination, source = self.Partner.create([
            {'name': 'Destination', 'is_company': True},
            {'name': 'Source', 'is_company': True},
        ])
        existing, transferred = self.Partner.create([
            {'name': 'Existing', 'parent_id': destination.id, 'active': False},
            {'name': 'Transferred', 'parent_id': source.id, 'active': False},
        ])
        grandchild = self.Partner.create({
            'name': 'Grandchild', 'parent_id': transferred.id, 'active': False,
        })
        self.env.invalidate_all()
        computed_ids = set()
        compute = self.registry['res.partner']._compute_complete_name

        def track_compute(partners):
            computed_ids.update(partners.ids)
            return compute(partners)

        with patch.object(self.registry['res.partner'], '_compute_complete_name', track_compute):
            self.env['base.partner.merge.automatic.wizard']._merge(
                (source + destination).ids, destination,
            )
            self.env.flush_all()

        self.assertNotIn(existing.id, computed_ids)
        self.assertIn(transferred.id, computed_ids)
        self.assertIn(grandchild.id, computed_ids)
        self.env.invalidate_all()
        self.assertEqual(transferred.parent_id, destination)
        self.assertEqual(transferred.complete_name, 'Destination, Transferred')
        self.assertEqual(grandchild.complete_name, 'Destination, Grandchild')

    def test_merge_recomputes_changed_destination_dependents(self):
        destination, source = self.Partner.create([
            {'name': False, 'is_company': True, 'type': 'delivery'},
            {'name': 'Source', 'is_company': True},
        ])
        child = self.Partner.create({
            'name': 'Existing', 'parent_id': destination.id, 'active': False,
        })
        self.env.invalidate_all()
        self.env['base.partner.merge.automatic.wizard']._merge(
            (source + destination).ids, destination,
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(destination.name, 'Source')
        self.assertEqual(child.complete_name, 'Source, Existing')

    def test_merge_recomputes_copied_company_dependent_value(self):
        self.addCleanup(self.registry.reset_changes)
        self.env['ir.model.fields'].create({
            'name': 'x_merge_company_code',
            'field_description': 'Company code',
            'model_id': self.env.ref('base.model_res_partner').id,
            'ttype': 'char',
            'company_dependent': True,
        })
        self.env['ir.model.fields'].create({
            'name': 'x_merge_code_snapshot',
            'field_description': 'Company code snapshot',
            'model_id': self.env.ref('base.model_res_partner').id,
            'ttype': 'char',
            'store': True,
            'depends': 'x_merge_company_code',
            'compute': "for record in self: record['x_merge_code_snapshot'] = record.x_merge_company_code",
        })
        other_company = self.env['res.company'].create({'name': 'Other company'})
        for company in self.env.company + other_company:
            with self.subTest(company=company.name):
                partners = self.Partner.with_company(company)
                destination, source = partners.create([
                    {'name': 'Destination', 'x_merge_company_code': False},
                    {'name': 'Source', 'x_merge_company_code': 'SOURCE-CODE'},
                ])
                partners.env.flush_all()
                partners.env.invalidate_all()
                self.assertFalse(destination.x_merge_code_snapshot)
                self.env['base.partner.merge.automatic.wizard'].with_company(company)._merge(
                    (source + destination).ids, destination,
                )
                partners.env.flush_all()
                partners.env.invalidate_all()
                self.assertEqual(destination.x_merge_company_code, 'SOURCE-CODE')
                self.assertEqual(destination.x_merge_code_snapshot, 'SOURCE-CODE')

    def test_merge_synchronizes_unchanged_values_to_children(self):
        destination, source = self.Partner.create([
            {'name': 'Destination', 'is_company': True, 'vat': 'DEST',
             'country_id': self.env.ref('base.us').id, 'company_id': self.env.company.id},
            {'name': 'Source', 'is_company': True, 'vat': 'SOURCE',
             'country_id': self.env.ref('base.ca').id, 'street': 'Source street',
             'company_id': False},
        ])
        child = self.Partner.create({
            'name': 'Child', 'parent_id': source.id, 'company_id': False,
        })
        self.env['base.partner.merge.automatic.wizard']._merge(
            (source + destination).ids, destination,
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(destination.street, 'Source street')
        self.assertEqual(child.parent_id, destination)
        self.assertEqual(child.company_id, destination.company_id)
        self.assertEqual(child.country_id, destination.country_id)
        self.assertEqual(child.vat, destination.vat)
        self.assertEqual(child.street, destination.street)

    def test_merge_sums_values(self):
        self.partner1.color = 3
        self.partner2.color = 5
        wizard = self.env['base.partner.merge.automatic.wizard']
        with patch.object(self.registry['base.partner.merge.automatic.wizard'], '_get_summable_fields', return_value=['color']):
            wizard._merge((self.partner1 + self.partner2).ids, self.partner1)
        self.assertEqual(self.partner1.color, 8)

    def test_merge_recomputes_related_company(self):
        company = self.env['res.company'].create({'name': 'Source company'})
        source = company.partner_id
        destination = self.Partner.create({'name': 'Destination company', 'is_company': True})
        self.env['base.partner.merge.automatic.wizard']._merge(
            (source + destination).ids, destination,
        )
        self.env.invalidate_all()
        self.assertEqual(company.partner_id, destination)
        self.assertEqual(company.name, destination.name)

    def test_merge_company_dependent_values(self):
        company = self.env['res.company'].create({'name': 'Other company'})
        self.partner1.barcode = False
        self.partner2.barcode = 'Source barcode'
        self.partner1.with_company(company).barcode = 'Other company barcode'
        self.partner2.with_company(company).barcode = 'Other source barcode'
        self.env['base.partner.merge.automatic.wizard']._merge(
            (self.partner1 + self.partner2).ids, self.partner1,
        )
        self.env.invalidate_all()
        self.assertEqual(self.partner1.barcode, 'Source barcode')
        self.assertEqual(self.partner1.with_company(company).barcode, 'Other company barcode')

    def test_merge_company_dependent_sums(self):
        self.addCleanup(self.registry.reset_changes)
        # Preserve assigned scores on recomputation while exercising the computed,
        # company-dependent summation branch.
        self.env['ir.model.fields'].create({
            'name': 'x_merge_score',
            'field_description': 'Merge score',
            'model_id': self.env.ref('base.model_res_partner').id,
            'ttype': 'integer',
            'company_dependent': True,
            'store': True,
            'depends': 'name',
            'compute': "for record in self: record['x_merge_score'] = record['x_merge_score']",
        })
        company = self.env['res.company'].create({'name': 'Other company'})
        commercial_fields = self.Partner._commercial_fields()
        wizard = self.env['base.partner.merge.automatic.wizard']
        for first, second, other_first, other_second in [(2, 5, 3, 7), (2, 0, 3, 0)]:
            with self.subTest(source_score=second):
                destination, source = self.Partner.create([
                    {'name': 'Destination'}, {'name': 'Source'},
                ])
                destination.x_merge_score = first
                source.x_merge_score = second
                destination.with_company(company).x_merge_score = other_first
                source.with_company(company).x_merge_score = other_second
                child = self.Partner.create({'name': 'Child', 'parent_id': source.id})
                child.x_merge_score = 99
                child.with_company(company).x_merge_score = 99
                with patch.object(self.registry['base.partner.merge.automatic.wizard'], '_get_summable_fields', return_value=['x_merge_score']), \
                     patch.object(self.registry['res.partner'], '_commercial_fields', return_value=commercial_fields + ['x_merge_score']):
                    wizard._merge((source + destination).ids, destination)
                self.env.invalidate_all()
                for partner in destination + child:
                    self.assertEqual(partner.x_merge_score, first + second)
                    self.assertEqual(partner.with_company(company).x_merge_score, other_first + other_second)
