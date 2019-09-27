from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSettings(AccountingTestCase):

    def test_switch_taxB2B_taxB2C(self):
        """
        Since having users both in the tax B2B and tax B2C groups raise,
        modifications of the settings must be done in the right order;
        otherwise it is impossible to change the settings.
        """
        # at each setting change, all users should be removed from one group and added to the other
        # so picking an arbitrary witness should be equivalent to checking that everything worked.
        config = self.env['res.config.settings'].create({})

        config.show_line_subtotals_tax_selection = "tax_excluded"
        config._onchange_sale_tax()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), True)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), False)

        config.show_line_subtotals_tax_selection = "tax_included"
        config._onchange_sale_tax()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), False)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), True)

        config.show_line_subtotals_tax_selection = "tax_excluded"
        config._onchange_sale_tax()
        config.execute()
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_excluded'), True)
        self.assertEqual(self.env.user.has_group('account.group_show_line_subtotals_tax_included'), False)
