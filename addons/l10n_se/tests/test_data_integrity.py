# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Consistency of the bundled data, checked without loading it.

Guards against regressions when BAS, the VAT return or the SRU field tables change.
"""
import csv
import io
import re

from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open

from odoo.addons.l10n_se.models.l10n_se_sru_mapping import _parse_expression

# Amount fields of Skatteverket's field tables (fältnamnstabeller), package 2026P4
SKV_2026P4_FIELDS = {
    'ink2': {
        '7201', '7202', '7214', '7215', '7216', '7217', '7230', '7231', '7232', '7233', '7234', '7235',
        '7241', '7242', '7243', '7244', '7245', '7246', '7251', '7252', '7261', '7262', '7263', '7270',
        '7271', '7281', '7301', '7302', '7321', '7322', '7323', '7331', '7332', '7333', '7350', '7351',
        '7352', '7353', '7354', '7360', '7361', '7362', '7363', '7364', '7365', '7366', '7367', '7368',
        '7369', '7370', '7410', '7411', '7412', '7413', '7414', '7415', '7416', '7417', '7419', '7420',
        '7421', '7422', '7423', '7450', '7510', '7511', '7512', '7513', '7514', '7515', '7516', '7517',
        '7518', '7519', '7520', '7521', '7522', '7524', '7525', '7526', '7527', '7528', '7530', '7550',
    },
    'ink3': {
        '8650', '8651', '8652', '8653', '8654', '8655', '8656', '8657', '8659', '8660', '8663', '8671',
        '8672', '8673', '8674', '8675', '8676', '8677', '8679', '8680', '8685', '8720', '8721', '8722',
        '8723', '8724', '8725', '8726', '8727', '8728', '8729', '8730', '8735', '8736', '8737', '8738',
        '8739', '8740', '8741', '8742', '8743', '8744', '8750', '8751', '8752', '8753', '8754', '8755',
        '8756', '8757', '8758', '8760', '8761', '8762', '8763', '8770', '8771', '8772', '8773', '8774',
        '8775', '8776', '8777', '8778', '8780', '8781', '8785',
    },
    'ink4': {
        '7201', '7202', '7214', '7215', '7216', '7217', '7232', '7234', '7236', '7237', '7245', '7246',
        '7247', '7253', '7263', '7264', '7272', '7281', '7310', '7311', '7312', '7313', '7314', '7322',
        '7323', '7331', '7332', '7333', '7353', '7355', '7362', '7363', '7365', '7368', '7370', '7371',
        '7410', '7411', '7412', '7413', '7414', '7415', '7416', '7417', '7427', '7450', '7510', '7511',
        '7512', '7513', '7514', '7515', '7518', '7519', '7520', '7521', '7522', '7535', '7537', '7550',
    },
    'ne': {
        '7200', '7210', '7211', '7212', '7213', '7240', '7250', '7260', '7280', '7300', '7320', '7330',
        '7380', '7381', '7382', '7383', '7400', '7401', '7402', '7403', '7440', '7500', '7501', '7502',
        '7503', '7504', '7505', '7600', '7601', '7602', '7603', '7604', '7605', '7606', '7607', '7608',
        '7609', '7610', '7611', '7612', '7613', '7614', '7630', '7700', '7701', '7702', '7703', '7704',
        '7705', '7706', '7707', '7708', '7709', '7710', '7711', '7712', '7713', '7714', '7730', '8002',
        '8003', '8004', '8006', '8007', '8009', '8010', '8011', '8012',
    },
}

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
                self.assertFalse([c for c in codes if c.startswith('19')], "bank and cash accounts are created by Odoo")
                self.assertFalse([a['code'] for a in accounts if not a.get('name@sv_SE')], "Swedish name missing")
                self.assertFalse([a['code'] for a in accounts
                                  if a['account_type'] in ('asset_receivable', 'liability_payable') and a['reconcile'] != 'True'],
                                 "receivable/payable accounts must be reconcilable")

    def test_tax_tags_in_report(self):
        with file_open('l10n_se/data/account_tax_report_data.xml', 'r') as f:
            report_codes = set(re.findall(r'<field name="formula">-?(se_\w+)</field>', f.read()))
        tags = {tag for row in self.taxes for tag in row['repartition_line_ids/tag_ids'].split('||') if tag}
        self.assertFalse(tags - report_codes, "tax tags without a box in the VAT return")

    def test_sru_codes_exist_at_skatteverket(self):
        for sru_type, fields in SKV_2026P4_FIELDS.items():
            with self.subTest(sru_type=sru_type):
                rows = _rows(f'{sru_type}_sru_template.csv')
                self.assertFalse({r['sru_code'] for r in rows} - fields, "SRU codes unknown to Skatteverket")
                self.assertFalse([r['account_expression'] for r in rows if _parse_expression(r['account_expression']) is None])
