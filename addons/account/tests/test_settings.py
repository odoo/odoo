# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSettings(AccountTestInvoicingCommon):

    def test_switch_taxB2B_taxB2C(self):
        """
        Since having users both in the tax B2B and tax B2C groups raise,
        modifications of the settings must be done in the right order;
        otherwise it is impossible to change the settings.
        """
        # at each setting change, all users should be removed from one group and added to the other
        # so picking an arbitrary witness should be equivalent to checking that everything worked.
        config = self.env['res.config.settings'].create({})
        self.switch_tax_settings(config)

    def switch_tax_settings(self, config):
        config.show_line_subtotals_tax_selection = "tax_excluded"
        config.flush_recordset()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), True)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), False)

        config.show_line_subtotals_tax_selection = "tax_included"
        config.flush_recordset()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), False)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), True)

        config.show_line_subtotals_tax_selection = "tax_excluded"
        config.flush_recordset()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), True)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), False)

    def test_switch_taxB2B_taxB2C_multicompany(self):
        """
           Contrarily to the (apparently reasonable) assumption that adding users
           to group and removing them was symmetrical, it may not be the case
           if one is done in SQL and the other via the ORM.
           Because the latter automatically takes into account record rules that
           might make some users invisible.

           This one is identical to the previous, except that we do the actions
           with a non-superuser user, and in a new company with one user in common
           with another company which has a different taxB2X setting.
        """
        user = self.env.ref('base.user_admin')
        company = self.env['res.company'].create({'name': 'oobO'})
        user.write({'company_ids': [(4, company.id)], 'company_id': company.id})
        Settings = self.env['res.config.settings'].with_user(user.id)
        config = Settings.create({})

        self.switch_tax_settings(config)

    def test_switch_company_currency(self):
        """
        A user should not be able to switch the currency of another company
        when that company already has posted account move lines.
        """
        # Create company A (user's company)
        company_a = self.env['res.company'].create({
            'name': "Company A",
        })

        # Get company B from test setup
        company_b = self.company_data['company']

        # Create a purchase journal for company B
        journal = self.env['account.journal'].create({
            'name': "Vendor Bills Journal",
            'code': "VEND",
            'type': "purchase",
            'company_id': company_b.id,
            'currency_id': company_b.currency_id.id,
        })

        # Create an invoice for company B
        invoice = self.env['account.move'].create({
            'move_type': "in_invoice",
            'company_id': company_b.id,
            'journal_id': journal.id,
        })
        invoice.currency_id = self.env.ref('base.EUR').id

        # Add a line to the invoice using an expense account
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': self.company_data["default_account_expense"].id,
            'name': "Test Invoice Line",
            'company_id': company_b.id,
        })

        # Create a user that only belongs to company A
        user = self.env['res.users'].create({
            'name': "User A",
            'login': "user_a@example.com",
            'email': "user_a@example.com",
            'company_id': company_a.id,
            'company_ids': [Command.set([company_a.id])],
            'groups_id': [Command.set([
                self.env.ref('base.group_system').id,
                self.env.ref('base.group_erp_manager').id,
                self.env.ref('account.group_account_user').id,
            ])],
        })

        # Try to change company B's currency as user A (should raise UserError)
        user_env = self.env(user=user)
        with self.assertRaises(UserError):
            user_env['res.company'].browse(company_b.id).write({
                'currency_id': self.env.ref('base.EUR').id,
            })
