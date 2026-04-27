# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests import tagged
import logging

from odoo.addons.l10n_in_reports.tests.common import L10nInTestAccountReportsCommon


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(L10nInTestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.init_invoice(
            move_type='out_invoice',
            products=cls.product_a,
            post=True,
        )

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        # TODO: default_account_tax_sale is not set when default_tax is group of tax
        # so when this method is called it's raise error so by overwrite this and stop call supper.
        return cls.env["account.tax"]

    def test_gstr1_b2b_summary(self):
        report = self.env.ref('l10n_in_reports.account_report_gstr1')
        options = self._generate_options(report, fields.Date.from_string("2019-01-01"), fields.Date.from_string("2019-12-31"))
        b2b_line = report._get_lines(options)[0]
        columns = {col.get('expression_label'): col.get('no_format') for col in b2b_line.get('columns')}
        # For B2B Invoice - 4A, AB, 4C, 6B, 6C
        expected = {
            'name': 'B2B Invoice - 4A, 4B, 4C, 6B, 6C',
            'tax_base': 1000.0,
            'tax_cgst': 25.0,
            'tax_sgst': 25.0,
            'tax_igst': 0.0,
            'tax_cess': 0.0
        }
        self.assertDictEqual(expected, {'name': b2b_line.get('name'), **columns}, "Wrong values for Indian GSTR-1 B2B summary report.")
