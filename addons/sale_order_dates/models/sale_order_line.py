# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_order_line_procurement(self, group_id):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        for line in self.filtered(lambda x: x.order_id.requested_date):
            date_planned = fields.Datetime.from_string(line.order_id.requested_date) - timedelta(days=line.order_id.company_id.security_lead)
            vals.update({
                'date_planned': fields.Datetime.to_string(date_planned),
            })
        return vals
