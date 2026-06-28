# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import HttpCase, tagged

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


@tagged('post_install', '-at_install')
class TestPricelistReportController(ProductCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist = cls._enable_pricelists()

    def test_csv_export(self):
        self.authenticate('admin', 'admin')
        response = self.url_open(
            "/product/export/pricelist/",
            data={
                "report_data": json.dumps({
                    "active_model": "product.template",
                    "active_ids": list(self.env['product.template']._search([], limit=10)),
                    "display_pricelist_title": "",
                    "pricelist_id": self.pricelist.id,
                    "quantities": [1, 5, 10],
                    "date": "2026-04-20",
                }),
                "export_format": "csv",
                "csrf_token": self.csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_xlsx_export(self):
        self.authenticate('admin', 'admin')
        response = self.url_open(
            "/product/export/pricelist/",
            data={
                "report_data": json.dumps({
                    "active_model": "product.template",
                    "active_ids": list(self.env['product.template']._search([], limit=10)),
                    "display_pricelist_title": "",
                    "pricelist_id": self.pricelist.id,
                    "quantities": [1, 5, 10],
                    "date": "2026-04-20",
                }),
                "export_format": "xlsx",
                "csrf_token": self.csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 200)
