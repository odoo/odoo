# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Consistency of the bundled data, checked without loading it.

Guards against regressions when BAS or the VAT return change.
"""
import csv
import io
import re

from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open

CHARTS = {
    'se_K1': ('se_K1',),
    'se_K2': ('se_K2',),
    'se_K3': ('se_K2', 'se_K3'),
    'se_K2_HB': ('se_K2', 'se_K2_HB'),
    'se_K2_NPO': ('se_K2', 'se_K2_NPO'),
}


def _rows(name):
    with file_open(f'l10n_se/data/template/{name}', 'r') as f:
        return list(csv.DictReader(io.StringIO(f.read())))


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeDataIntegrity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accounts = {code: _rows(f'account.account-{code}.csv') for code in ('se_K1', 'se_K2', 'se_K3', 'se_K2_HB', 'se_K2_NPO')}
        cls.taxes = _rows('account.tax-se.csv')
        cls.fiscal_positions = _rows('account.fiscal.position-se.csv')

    def _chart_accounts(self, chart):
        return [account for part in CHARTS[chart] for account in self.accounts[part]]

    def test_account_references(self):
        """Every account used by the taxes and fiscal positions exists in every chart."""
        used = {row['repartition_line_ids/account_id'] for row in self.taxes if row['repartition_line_ids/account_id']}
        used |= {row[key] for row in self.fiscal_positions
                 for key in ('account_ids/account_src_id', 'account_ids/account_dest_id') if row.get(key)}
        for chart in CHARTS:
            with self.subTest(chart=chart):
                ids = {account['id'] for account in self._chart_accounts(chart)}
                self.assertFalse(used - ids, f"missing accounts in {chart}")

    def test_accounts(self):
        for chart in CHARTS:
            with self.subTest(chart=chart):
                accounts = self._chart_accounts(chart)
                codes = [account['code'] for account in accounts]
                self.assertEqual(len(codes), len(set(codes)), "duplicate account codes")
                self.assertFalse([c for c in codes if c.startswith(('191', '192', '193'))],
                                 "cash and bank accounts (1910-1939) are created by the journals")
                self.assertFalse([a['code'] for a in accounts if not a.get('name@sv_SE')], "Swedish name missing")
                self.assertFalse([a['code'] for a in accounts
                                  if a['account_type'] in ('asset_receivable', 'liability_payable') and a['reconcile'] != 'True'],
                                 "receivable/payable accounts must be reconcilable")

    def test_tax_tags_in_report(self):
        with file_open('l10n_se/data/account_tax_report_data.xml', 'r') as f:
            report_codes = set(re.findall(r'<field name="formula">-?(se_\w+)</field>', f.read()))
        tags = {tag for row in self.taxes for tag in row['repartition_line_ids/tag_ids'].split('||') if tag}
        self.assertFalse(tags - report_codes, "tax tags without a box in the VAT return")
