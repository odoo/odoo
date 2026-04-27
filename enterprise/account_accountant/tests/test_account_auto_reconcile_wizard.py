from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountAutoReconcileWizard(AccountTestInvoicingCommon):
    """ Tests the account automatic reconciliation and its wizard. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.comp_curr = cls.company_data['currency']
        cls.foreign_curr = cls.setup_other_currency('EUR')

        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.partners = cls.partner_a + cls.partner_b
        cls.receivable_account = cls.company_data['default_account_receivable']
        cls.payable_account = cls.company_data['default_account_payable']
        cls.revenue_account = cls.company_data['default_account_revenue']
        cls.test_date = fields.Date.from_string('2016-01-01')

    def _create_many_lines(self):
        self.line_1_group_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.line_2_group_1 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        self.line_3_group_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-03', partner=self.partner_a)
        self.line_4_group_1 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-04', partner=self.partner_a)
        self.line_5_group_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-05', partner=self.partner_a)
        self.group_1 = self.line_1_group_1 + self.line_2_group_1 + self.line_3_group_1 + self.line_4_group_1 + self.line_5_group_1

        self.line_1_group_2 = self.create_line_for_reconciliation(500.0, 500.0, self.comp_curr, '2016-01-01', partner=self.partner_b)
        self.line_2_group_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.comp_curr, '2016-01-01', partner=self.partner_b)
        self.line_3_group_2 = self.create_line_for_reconciliation(500.0, 500.0, self.comp_curr, '2017-01-02', partner=self.partner_b)
        self.line_4_group_2 = self.create_line_for_reconciliation(-500.0, -500.0, self.comp_curr, '2017-01-02', partner=self.partner_b)
        self.group_2 = self.line_1_group_2 + self.line_2_group_2 + self.line_3_group_2 + self.line_4_group_2

        self.line_1_group_3 = self.create_line_for_reconciliation(1500.0, 3000.0, self.foreign_curr, '2016-01-01', partner=self.partner_b)
        self.line_2_group_3 = self.create_line_for_reconciliation(-1000.0, -3000.0, self.foreign_curr, '2017-01-01', partner=self.partner_b)
        self.line_3_group_3 = self.create_line_for_reconciliation(3000.0, 3000.0, self.comp_curr, '2016-01-01', partner=self.partner_b)
        self.line_4_group_3 = self.create_line_for_reconciliation(-3000.0, -3000.0, self.comp_curr, '2016-01-01', partner=self.partner_b)
        self.group_3 = self.line_1_group_3 + self.line_2_group_3 + self.line_3_group_3 + self.line_4_group_3

        self.line_1_group_4 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', account_1=self.payable_account, partner=self.partner_a)
        self.line_2_group_4 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', account_1=self.payable_account, partner=self.partner_a)
        self.group_4 = self.line_1_group_4 + self.line_2_group_4

    def test_auto_reconcile_one_to_one(self):
        self._create_many_lines()
        should_be_reconciled = self.line_1_group_1 + self.line_2_group_1 + self.line_3_group_1 + self.line_4_group_1 \
                               + self.line_1_group_2 + self.line_2_group_2 \
                               + self.line_1_group_3 + self.line_2_group_3 + self.line_3_group_3 + self.line_4_group_3
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
            'partner_ids': self.partners.ids,
            'search_mode': 'one_to_one',
        })
        wizard.auto_reconcile()

        self.assertTrue(should_be_reconciled.full_reconcile_id)
        self.assertEqual(self.line_1_group_1.full_reconcile_id, self.line_2_group_1.full_reconcile_id,
                         "Entries should be reconciled together since they are in the same group and have closer dates.")
        self.assertEqual(self.line_3_group_1.full_reconcile_id, self.line_4_group_1.full_reconcile_id,
                         "Entries should be reconciled together since they are in the same group and have closer dates.")
        self.assertEqual(self.line_1_group_2.full_reconcile_id, self.line_1_group_2.full_reconcile_id,
                         "Entries should be reconciled together since they are in the same group and have closer dates.")
        self.assertEqual(self.line_1_group_3.full_reconcile_id, self.line_2_group_3.full_reconcile_id,
                         "Entries should be reconciled together since they are in the same group and have closer dates.")
        self.assertEqual(self.line_3_group_3.full_reconcile_id, self.line_4_group_3.full_reconcile_id,
                         "Entries should be reconciled together since they are in the same group and have closer dates.")
        self.assertNotEqual(self.line_2_group_3.full_reconcile_id, self.line_3_group_3.full_reconcile_id,
                            "Entries should NOT be reconciled together as they are of different currencies.")
        self.assertFalse(self.line_5_group_1.reconciled,
                         "This entry shouldn't be reconciled since group 1 has an odd number of lines, they can't all be reconciled, and it's the most recent one.")
        self.assertFalse((self.line_3_group_2 + self.line_4_group_2).full_reconcile_id,
                         "Entries shouldn't be reconciled since it's outside of accepted date range of the wizard.")
        self.assertFalse((self.line_1_group_4 + self.line_2_group_4).full_reconcile_id,
                         "Entries shouldn't be reconciled since their account is out of the wizard's scope.")

    def test_auto_reconcile_zero_balance(self):
        self._create_many_lines()
        should_be_reconciled = self.line_1_group_2 + self.line_2_group_2 + self.group_3
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
            'partner_ids': self.partners.ids,
            'search_mode': 'zero_balance',
        })
        wizard.auto_reconcile()

        self.assertTrue(should_be_reconciled.full_reconcile_id)
        self.assertFalse(self.group_1.full_reconcile_id,
                         "Entries shouldn't be reconciled since their total balance is not zero.")
        self.assertEqual((self.line_1_group_2 + self.line_2_group_2).mapped('matching_number'), [self.line_1_group_2.matching_number] * 2,
                         "Entries should be reconciled together as their total balance is zero.")
        self.assertEqual((self.line_1_group_3 + self.line_2_group_3).mapped('matching_number'), [self.line_1_group_3.matching_number] * 2,
                         "Entries should be reconciled together as their total balance is zero with the same currency.")
        self.assertEqual((self.line_3_group_3 + self.line_4_group_3).mapped('matching_number'), [self.line_3_group_3.matching_number] * 2,
                         "Lines 3 and 4 are reconciled but not with two first lines since their currency is different.")
        self.assertFalse(self.group_4.full_reconcile_id,
                         "Entries shouldn't be reonciled since their account is out of the wizard's scope.")

    def test_nothing_to_auto_reconcile(self):
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
            'partner_ids': self.partners.ids,
            'search_mode': 'zero_balance',
        })
        with self.assertRaises(UserError):
            wizard.auto_reconcile()

    def test_auto_reconcile_no_account_nor_partner_one_to_one(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
        })
        reconciled_amls = wizard._auto_reconcile_one_to_one()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_no_account_nor_partner_zero_balance(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
        })
        reconciled_amls = wizard._auto_reconcile_zero_balance()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_no_account_one_to_one(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'partner_ids': self.partners.ids,
        })
        reconciled_amls = wizard._auto_reconcile_one_to_one()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_no_account_zero_balance(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'partner_ids': self.partners.ids,
        })
        reconciled_amls = wizard._auto_reconcile_zero_balance()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_no_partner_one_to_one(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
        })
        reconciled_amls = wizard._auto_reconcile_one_to_one()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_no_partner_zero_balance(self):
        self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
        })
        reconciled_amls = wizard._auto_reconcile_zero_balance()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_rounding_one_to_one(self):
        """ Checks that two lines with different values, currency rounding aside, are reconciled in one-to-one mode. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        # Need to manually update the values to bypass ORM
        self.env.cr.execute(
            """
            UPDATE account_move_line SET amount_residual_currency = 1000.0000001 WHERE id = %(line_1_id)s;
            UPDATE account_move_line SET amount_residual_currency = -999.999999 WHERE id = %(line_2_id)s;
            """,
            {'line_1_id': line_1.id, 'line_2_id': line_2.id}
        )
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
        })
        reconciled_amls = wizard._auto_reconcile_one_to_one()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_auto_reconcile_rounding_zero_balance(self):
        """ Checks that two lines with different values, currency rounding aside, are reconciled in zero balance mode. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-01', partner=self.partner_a)
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-02', partner=self.partner_a)
        # Need to manually update the values to bypass ORM
        self.env.cr.execute(
            """
            UPDATE account_move_line SET amount_residual_currency = 1000.0000001 WHERE id = %(line_1_id)s;
            UPDATE account_move_line SET amount_residual_currency = -999.999999 WHERE id = %(line_2_id)s;
            """,
            {'line_1_id': line_1.id, 'line_2_id': line_2.id}
        )
        wizard = self.env['account.auto.reconcile.wizard'].new({
            'from_date': '2016-01-01',
            'to_date': '2017-01-01',
            'account_ids': self.receivable_account.ids,
        })
        reconciled_amls = wizard._auto_reconcile_zero_balance()
        self.assertTrue(reconciled_amls.full_reconcile_id)

    def test_preset_wizard(self):
        """ Tests that giving lines_ids to wizard presets correctly values. """
        line_1 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-30', partner=self.partner_a)
        line_2 = self.create_line_for_reconciliation(-1000.0, -1000.0, self.comp_curr, '2016-01-31', partner=self.partner_a)
        wizard = self.env['account.auto.reconcile.wizard'].with_context(domain=[('id', 'in', (line_1 + line_2).ids)]).create({})
        self.assertRecordValues(wizard, [{
            'account_ids': self.receivable_account.ids,
            'partner_ids': self.partner_a.ids,
            'from_date': fields.Date.from_string('2016-01-30'),
            'to_date': fields.Date.from_string('2016-01-31'),
            'search_mode': 'zero_balance',
        }])

        line_3 = self.create_line_for_reconciliation(1000.0, 1000.0, self.comp_curr, '2016-01-31', partner=self.partner_a)
        line_4 = self.create_line_for_reconciliation(-500.0, -500.0, self.comp_curr, '2016-02-28', partner=None)
        wizard = self.env['account.auto.reconcile.wizard'].with_context(domain=[('id', 'in', (line_3 + line_4).ids)]).create({})
        self.assertRecordValues(wizard, [{
            'account_ids': self.receivable_account.ids,
            'partner_ids': [],
            'from_date': fields.Date.from_string('2016-01-31'),
            'to_date': fields.Date.from_string('2016-02-28'),
            'search_mode': 'one_to_one',
        }])
