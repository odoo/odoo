from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestRgsTags(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()

    def _rgs_tag(self, code):
        return self.env.ref(f'l10n_nl.l10n_nl_account_tag_rgs_{code}')

    def test_new_bank_and_cash_journal_accounts(self):
        for journal_type, code in (('bank', 'BLimBanRba'), ('cash', 'BLimKasKas')):
            journal = self.env['account.journal'].create({
                'name': f'New {journal_type}',
                'type': journal_type,
                'code': 'NEWB' if journal_type == 'bank' else 'NEWC',
            })
            self.assertIn(self._rgs_tag(code), journal.default_account_id.tag_ids)

    def test_transfer_account(self):
        self.assertIn(self._rgs_tag('BLimKruSto'), self.env.company.transfer_account_id.tag_ids)

    def test_apply_default_rgs_tags_keeps_user_choice(self):
        bank_account = self.company_data['default_journal_bank'].default_account_id
        cash_account = self.company_data['default_journal_cash'].default_account_id
        user_tag = self._rgs_tag('BLimKruSto')
        bank_account.tag_ids = user_tag
        cash_account.tag_ids -= self._rgs_tag('BLimKasKas')
        transfer_account = self.env.company.transfer_account_id
        transfer_account.tag_ids -= self._rgs_tag('BLimKruSto')

        self.env['account.account']._l10n_nl_apply_default_rgs_tags(self.env.company)

        self.assertEqual(bank_account.tag_ids & user_tag, user_tag)
        self.assertNotIn(self._rgs_tag('BLimBanRba'), bank_account.tag_ids)
        self.assertIn(self._rgs_tag('BLimKasKas'), cash_account.tag_ids)
        self.assertIn(self._rgs_tag('BLimKruSto'), transfer_account.tag_ids)
