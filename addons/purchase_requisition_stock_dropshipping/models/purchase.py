# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        super()._onchange_requisition_id()
        if self.requisition_id and self.requisition_id.procurement_group_id:
            self.group_id = self.requisition_id.procurement_group_id.id
            if self.group_id.sale_id.partner_shipping_id:
                self.dest_address_id = self.group_id.sale_id.partner_shipping_id.id
