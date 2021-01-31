# ©  2008-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, models


class ProductCatalogReport(models.AbstractModel):
    _name = "report.deltatech_product_catalog.report_product_catalog"
    _template = "deltatech_product_catalog.report_product_catalog"
    _description = "ProductCatalogReport"

    @api.model
    def _get_report_values(self, docids, data=None):
        products = self.env["product.template"].browse(docids)

        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        docargs = {
            "data": data,
            "doc_ids": docids,
            "doc_model": report.model,
            "docs": products,
        }
        return docargs


class CategoryCatalogReport(models.AbstractModel):
    _name = "report.deltatech_product_catalog.report_category_catalog"
    _template = "deltatech_product_catalog.report_category_catalog"
    _description = "CategoryCatalogReport"

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [("public_categ_ids", "child_of", docids)]
        products = self.env["product.template"].search(domain)

        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        docargs = {"data": data, "doc_ids": docids, "doc_model": report.model, "docs": products}
        return docargs
