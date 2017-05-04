# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import pycompat


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def make_mo(self):
        """ override method to set link in production created from sale order."""
        res = super(ProcurementOrder, self).make_mo()
        for procurement_id, production_id in pycompat.items(res):
            if production_id:
                production = self.env['mrp.production'].browse(production_id)
                move = production._get_parent_move(production.move_finished_ids[0])
                sale_order = move.procurement_id.sale_line_id.order_id
                if sale_order:
                    production.message_post_with_view('mail.message_origin_link',
                            values={'self': production, 'origin': sale_order},
                            subtype_id=self.env.ref('mail.mt_note').id)
        return res
