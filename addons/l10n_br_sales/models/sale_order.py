# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import sale


class SaleOrder(sale.SaleOrder):

    def _get_name_portal_content_view(self):
        self.ensure_one()
        return 'l10n_br_sales.sale_order_portal_content_brazil' if self.company_id.country_code == 'BR' else super()._get_name_portal_content_view()

    def _get_name_tax_totals_view(self):
        self.ensure_one()
        return 'l10n_br_sales.document_tax_totals_brazil' if self.company_id.country_code == 'BR' else super()._get_name_tax_totals_view()
