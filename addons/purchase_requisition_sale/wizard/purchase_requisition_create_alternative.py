# -*- coding: utf-8 -*-
from odoo.addons import purchase_requisition
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseRequisitionCreateAlternative(models.TransientModel, purchase_requisition.PurchaseRequisitionCreateAlternative):

    @api.model
    def _get_alternative_line_value(self, order_line):
        res_line = super()._get_alternative_line_value(order_line)
        if order_line.sale_line_id:
            res_line['sale_line_id'] = order_line.sale_line_id.id

        return res_line
