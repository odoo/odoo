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
        config.show_line_subtotals_tax_selection = "tax_included"
        self.assertEqual(self.env.user.company_id.show_line_subtotals_tax_selection, "tax_included")


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

        Settings = self.env['res.config.settings'].with_user(self.env.user.id)
        config = Settings.create({})
        config.show_line_subtotals_tax_selection = "tax_included"
        self.assertEqual(self.env.user.company_id.show_line_subtotals_tax_selection, "tax_included")

        self.env.user.company_id = self.company_data_2["company"].id
        self.assertEqual(self.env.user.company_id.show_line_subtotals_tax_selection, "tax_excluded")
