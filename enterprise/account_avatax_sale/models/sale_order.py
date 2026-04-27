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
