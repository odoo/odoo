# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, models


class PurchaseRequisitionCreateAlternative(models.TransientModel):
    _inherit = 'purchase.requisition.create.alternative'

    def _get_alternative_values(self):
        vals = super(PurchaseRequisitionCreateAlternative, self)._get_alternative_values()
        for val in vals:
            val.update({
                'picking_type_id': self.origin_po_id.picking_type_id.id,
                'group_id': self.origin_po_id.group_id.id,
            })
        return vals

    @api.model
    def _get_alternative_line_value(self, order_line, product_tmpl_ids_with_description):
        res_line = super()._get_alternative_line_value(order_line, product_tmpl_ids_with_description)
        if order_line.move_dest_ids:
            res_line['move_dest_ids'] = [Command.set(order_line.move_dest_ids.ids)]
        if order_line.group_id:
            res_line['group_id'] = order_line.group_id.id

        return res_line
