from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_mx.tests.common import TestMxCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountAccount(TestMxCommon):

    _test_groups = None  # FIXME list needed groups

    def test_create_account_without_code(self):
        """
        Test that creating an account without a code assigns the correct tag
        based on the account internal group.
        """
        debit_account, credit_account, off_balance_account = self.env['account.account'].create([
            {
                'name': "Debit Account",
                'account_type': 'asset_receivable',
                'company_ids': [Command.link(self.company_data['company'].id)],
            },
            {
                'name': "Credit Account",
                'account_type': 'liability_current',
                'company_ids': [Command.link(self.company_data['company'].id)],
            },
            {
                'name': "Off Balance Account",
                'account_type': 'off_balance',
                'company_ids': [Command.link(self.company_data['company'].id)],
            },
        ])

        self.assertEqual(debit_account.internal_group, 'asset')
        self.assertEqual(debit_account.tag_ids, self.env.ref('l10n_mx.tag_debit_balance_account'))

        self.assertEqual(credit_account.internal_group, 'liability')
        self.assertEqual(credit_account.tag_ids, self.env.ref('l10n_mx.tag_credit_balance_account'))

        self.assertEqual(off_balance_account.internal_group, 'off')
        self.assertFalse(off_balance_account.tag_ids)
