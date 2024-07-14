# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['account.avatax.unique.code', 'sale.order']

    def _get_avatax_dates(self):
        return self._get_date_for_external_taxes(), self._get_date_for_external_taxes()

    def _get_avatax_document_type(self):
        return 'SalesOrder'

    def _get_avatax_description(self):
        return 'Sales Order'

    def _get_invoice_grouping_keys(self):
        res = super()._get_invoice_grouping_keys()
        if self.filtered('fiscal_position_id.is_avatax'):
            res += ['partner_shipping_id']
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _without_invoice_line_taxes(self):
        without = super()._without_invoice_line_taxes()
        return without and not self.order_id.fiscal_position_id.is_avatax
