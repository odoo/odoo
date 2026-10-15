# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nVNAccountCodes(AccountTestInvoicingCommon):
    """ Test the codes of the Vietnamese chart of accounts """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('vn')
    def setUpClass(cls):
        super().setUpClass()

    def test_level_1_accounts_keep_their_three_digits(self):
        """ Circular 200/2014/TT-BTC numbers the level 1 accounts on three digits,
            they must not be padded to the width of the level 2 ones. """
        level_1_codes = ['111', '112', '113', '511', '632', '911']
        accounts = self.env['account.account'].search([('code', 'in', level_1_codes)])
        self.assertEqual(sorted(accounts.mapped('code')), level_1_codes)

    def test_new_journals_stay_in_their_account_family(self):
        """ The code of a new journal account is built from the prefixes, they have to
            point inside the level 2 accounts, not next to the level 1 ones. """
        Journal = self.env['account.journal']
        bank = Journal.create({'name': "New Bank", 'type': 'bank'})
        cash = Journal.create({'name': "New Cash", 'type': 'cash'})
        self.assertTrue(bank.default_account_id.code.startswith('112'))
        self.assertTrue(cash.default_account_id.code.startswith('111'))
