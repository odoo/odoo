# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests import tagged

from .common import SeAccountTestCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeSruAccounting(SeAccountTestCommon):
    """SRU codes resolved from real journal entries (balances via _read_group)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['l10n_se.sru.mapping'].load_template_from_file('ink2')
        cls.date = fields.Date.from_string('2026-03-15')

    def _entry(self, lines, post=True, company=None, date=None):
        company = company or self.env.company
        ChartTemplate = self.env['account.chart.template'].with_company(company)
        journal = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'general')], limit=1)
        move = self.env['account.move'].with_company(company).create({
            'move_type': 'entry',
            'date': date or self.date,
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {'account_id': ChartTemplate.ref(f'a{code}').id, 'debit': max(amount, 0), 'credit': max(-amount, 0)})
                for code, amount in lines
            ],
        })
        if post:
            move.action_post()
        return move

    def test_codes_from_posted_entries(self):
        self._entry([('1510', 1250), ('3001', -1000), ('2611', -250)])
        self._entry([('4010', 300), ('2440', -300)])
        codes = self.env['l10n_se.sru.mapping'].get_sru_codes_for_accounts('2026-01-01', '2026-12-31')
        self.assertEqual(codes.get('1510'), '7251')   # 2.26 kundfordringar
        self.assertEqual(codes.get('3001'), '7410')   # 3.1 nettoomsattning
        self.assertEqual(codes.get('2611'), '7369')   # 2.49 ovriga skulder
        self.assertEqual(codes.get('4010'), '7512')   # 3.6 handelsvaror (BAS 2026)
        self.assertEqual(codes.get('2440'), '7365')   # 2.45 leverantorsskulder

    def test_draft_entries(self):
        self._entry([('6110', 50), ('2440', -50)], post=False)
        SruMapping = self.env['l10n_se.sru.mapping']
        self.assertNotIn('6110', SruMapping.get_sru_codes_for_accounts('2026-01-01', '2026-12-31'))
        with_drafts = SruMapping.get_sru_codes_for_accounts('2026-01-01', '2026-12-31', include_unposted=True)
        self.assertEqual(with_drafts.get('6110'), '7513')  # 3.7 ovriga externa kostnader

    def test_period_and_company_isolation(self):
        self._entry([('1510', 100), ('3001', -100)])
        other = self._create_company(name='Annat AB')
        self.env.user.company_ids |= other
        self._entry([('3740', -10), ('1510', 10)], company=other)
        SruMapping = self.env['l10n_se.sru.mapping']
        codes = SruMapping.get_sru_codes_for_accounts('2026-01-01', '2026-12-31')
        self.assertNotIn('3740', codes, "another company's entries must not be included")
        self.assertFalse(SruMapping.get_sru_codes_for_accounts('2025-01-01', '2025-12-31'), "outside the period")

    def test_balance_sheet_closing_balance(self):
        """Balance sheet accounts are reported with their closing balance, P&L accounts with the year's movements."""
        self._entry([('1510', 500), ('3001', -500)], date=fields.Date.from_string('2025-06-30'))
        self._entry([('1510', 100), ('3001', -100)])
        balances = self.env['l10n_se.sru.mapping']._fetch_account_balances(
            self.env.company, fields.Date.from_string('2026-01-01'), fields.Date.from_string('2026-12-31'), False,
        )
        self.assertEqual(balances.get('1510'), 600, "closing balance including previous years")
        self.assertEqual(balances.get('3001'), -100, "only the income of the year")
