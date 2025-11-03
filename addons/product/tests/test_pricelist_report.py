# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestPricelistReport(ProductCommon):

    def test_product_template_pricelist_report(self):
        """Load report for `product.template` records."""
        self.env['report.product.report_pricelist'].get_html(data={
            'active_ids': self.env['product.template'].search([]).ids,
        })
        # Empty report
        self.env['report.product.report_pricelist'].get_html(data={})

    def test_product_product_pricelist_report(self):
        """Load report for `product.product` records."""
        self.env['report.product.report_pricelist'].get_html(data={
            'active_ids': self.env['product.product'].search([]).ids,
            'active_model': self.env['product.product']._name,
        })
        # Empty report
        self.env['report.product.report_pricelist'].get_html(data={
            'active_model': self.env['product.product']._name,
        })

    def test_no_pricelist_report(self):
        """Load report when there is no active pricelist.

        Report should fall back on company currency, and hide pricelist choices.
        """
        self.env['product.pricelist'].search([]).action_archive()
        self.env['report.product.report_pricelist'].get_html(data={
            'active_ids': self.env['product.template'].search([]).ids,
        })
