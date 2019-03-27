# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_subcontract_bom(self):
        self.ensure_one()
        bom = self.env['mrp.bom']._bom_subcontract_find(
            product=self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        if not bom:
            bom = self.env['mrp.bom']._bom_subcontract_find(
                product=self.product_id,
                picking_type=self.picking_type_id,
                company_id=self.company_id.id,
                bom_type='subcontract',
            )

        return bom

    def _action_confirm(self, merge=True, merge_into=False):
        res = super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)
        subcontract_details = []
        for move in res:
            if not move.picking_id:
                continue
            if not move.picking_id._is_subcontract():
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                error_message = _('Please define a BoM of type subcontracting for the product "%s". If you don\'t want to subcontract the product "%s", do not select a partner of type subcontractor.')
                error_message += '\n\n'
                error_message += _('If there is well a BoM of type subcontracting defined, check if you have set the correct subcontractors on it.')
                raise UserError(error_message % (move.product_id.name, move.product_id.name))
            subcontract_details.append((move, bom))
            move.picking_id._subcontracted_produce(subcontract_details)
        return res
