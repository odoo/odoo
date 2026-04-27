from odoo import fields

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestAECorporateTaxReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({
            'name': 'Threshold Test LLC',
            'country_id': cls.env.ref('base.ae').id,
        })
        asset_acc = cls.env['account.account'].create({
            'name': 'CIT Counterpart', 'code': 'CITC',
            'account_type': 'asset_current',
            'company_ids': [cls.company.id],
        })
        lia_acc = cls.env['account.account'].create({
            'name': 'CIT Liability', 'code': 'CITL',
            'account_type': 'liability_current',
            'company_ids': [cls.company.id],
        })
        cls.company.write({
            'l10n_ae_tax_report_counterpart_account': asset_acc.id,
            'l10n_ae_tax_report_liabilities_account': lia_acc.id,
        })

        cls.handler = cls.env['l10n_ae.corporate.tax.report.handler']
        cls.report = cls.env.ref('l10n_ae_corporate_tax_report.ae_corporate_tax_report')
        cls.options = cls.report.get_options({'report_id': cls.report.id})

    @staticmethod
    def _get_value(lines, line_name):
        return next(line for line in lines if line['name'] == line_name)['columns'][0]['no_format']

    def test_threshold_behavior(self):
        """Taxable Amount and Corporate TAX Amount must be 0 when Gross Profit ≤ 375,000,
        and properly computed when above."""
        self.init_invoice(
            'out_invoice',
            invoice_date=fields.Date.today(),
            amounts=[200_000.0],
            post=True,
        )
        lines = self.report._get_lines(self.options)
        taxable = self._get_value(lines, 'Taxable Amount')
        tax = self._get_value(lines, 'Corporate TAX Amount')
        self.assertEqual(taxable, 0.0, "Taxable Amount must be 0 below 375k threshold")
        self.assertEqual(tax, 0.0, "Corporate TAX Amount must be 0 below threshold")

        # Add another invoice to exceed the threshold
        self.init_invoice(
            'out_invoice',
            invoice_date=fields.Date.today(),
            amounts=[200_000.0],
            post=True,
        )
        lines = self.report._get_lines(self.options)
        taxable = self._get_value(lines, 'Taxable Amount')
        tax = self._get_value(lines, 'Corporate TAX Amount')
        self.assertEqual(taxable, 25000.0, "Taxable Amount should be gross  375k when above threshold")
        self.assertEqual(tax, 2250.0, "Corporate TAX Amount should be taxable 9%")
