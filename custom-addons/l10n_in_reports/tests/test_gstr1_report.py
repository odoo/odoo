# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
import logging
from odoo.tools.misc import NON_BREAKING_SPACE


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="in"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        cls.company_data["company"].write({
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street1",
            "city": "city1",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            })
        cls.partner_a.write({
            "vat": "24BBBFF5679L8ZR",
            "state_id": cls.env.ref("base.state_in_gj").id,
            "street": "street2",
            "city": "city2",
            "zip": "123456",
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
            })
        cls.product_a.write({"l10n_in_hsn_code": "01111"})
        cls.invoice = cls.init_invoice(
            "out_invoice",
            post=True,
            products=cls.product_a,
            taxes=cls.env["account.chart.template"].ref("sgst_sale_5")
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
