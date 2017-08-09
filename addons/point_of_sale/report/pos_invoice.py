# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class PosInvoiceReport(models.AbstractModel):
    _name = 'report.point_of_sale.report_invoice'

    @api.model
    def get_report_values(self, docids, data=None):
        PosOrder = self.env['pos.order']
        ids_to_print = []
        invoiced_posorders_ids = []
        selected_orders = PosOrder.browse(docids)
        for order in selected_orders.filtered(lambda o: o.invoice_id):
            ids_to_print.append(order.invoice_id.id)
            invoiced_posorders_ids.append(order.id)
        not_invoiced_orders_ids = list(set(docids) - set(invoiced_posorders_ids))
        if not_invoiced_orders_ids:
            not_invoiced_posorders = PosOrder.browse(not_invoiced_orders_ids)
            not_invoiced_orders_names = [a.name for a in not_invoiced_posorders]
            raise UserError(_('No link to an invoice for %s.') % ', '.join(not_invoiced_orders_names))

        return {'docs': self.env['account.invoice'].sudo().browse(ids_to_print)}
