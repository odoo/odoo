# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
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
