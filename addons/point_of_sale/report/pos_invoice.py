# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class PosInvoiceReport(osv.AbstractModel):
    _name = 'report.point_of_sale.report_invoice'

    def render_html(self, cr, uid, ids, data=None, context=None):
        if not isinstance(data, dict):
            data = {}
        report_obj = self.pool['report']
        posorder_obj = self.pool['pos.order']
        selected_orders = posorder_obj.browse(cr, uid, ids, context=context)
        ids_to_print = []
        invoiced_posorders_ids = []
        for order in selected_orders:
            if order.invoice_id:
                ids_to_print.append(order.invoice_id.id)
                invoiced_posorders_ids.append(order.id)

        not_invoiced_orders_ids = list(set(ids) - set(invoiced_posorders_ids))
        if not_invoiced_orders_ids:
            not_invoiced_posorders = posorder_obj.browse(cr, uid, not_invoiced_orders_ids, context=context)
            not_invoiced_orders_names = list(map(lambda a: a.name, not_invoiced_posorders))
            raise UserError(_('No link to an invoice for %s.') % ', '.join(not_invoiced_orders_names))

        data.update({
            'docs': self.pool['account.invoice'].browse(cr, uid, ids_to_print, context=context)
        })
        sup = super(PosInvoiceReport, self)
        if hasattr(sup, 'render_html'):
            return sup.render_html(cr, SUPERUSER_ID, ids, data, context=context)
        return report_obj.render(cr, SUPERUSER_ID, ids, 'account.report_invoice', data, context=context)
