# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import purchase_requisition


class PurchaseRequisitionCreateAlternative(purchase_requisition.PurchaseRequisitionCreateAlternative):

    @api.model
    def _get_alternative_line_value(self, order_line):
        res_line = super()._get_alternative_line_value(order_line)
        if order_line.sale_line_id:
            res_line['sale_line_id'] = order_line.sale_line_id.id

        return res_line
