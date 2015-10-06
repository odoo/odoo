# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrderLine(osv.osv):
    _inherit = 'sale.order.line'

    def _prepare_order_line_procurement(self, cr, uid, ids, group_id=False, context=None):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(cr, uid, ids, group_id=group_id, context=context)
        line = self.browse(cr, uid, ids, context=context)
        if line.order_id.requested_date:
            date_planned = datetime.strptime(line.order_id.requested_date, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(days=line.order_id.company_id.security_lead)
            vals.update({
                'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            })
        return vals
