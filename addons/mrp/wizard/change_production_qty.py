# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class ChangeProductionQty(models.TransientModel):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'

    # TDE FIXME: add production_id field
    mo_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True)
    product_qty = fields.Float(
        'Product Qty',
        digits=dp.get_precision('Product Unit of Measure'), required=True)

    @api.model
    def default_get(self, fields):
        res = super(ChangeProductionQty, self).default_get(fields)
        if 'mo_id' in fields and not res.get('mo_id') and self._context.get('active_model') == 'mrp.production' and self._context.get('active_id'):
            res['mo_id'] = self._context['active_id']
        if 'product_qty' in fields and not res.get('product_qty') and res.get('mo_id'):
            res['product_qty'] = self.env['mrp.production'].browse(res.get['mo_id']).product_qty
        return res

    @api.model
    def _update_product_to_produce(self, production, qty):
        production_move = production.move_finished_ids.filtered(lambda x:x.product_id.id == production.product_id.id and x.state not in ('done', 'cancel'))
        if production_move:
            production_move.write({'product_uom_qty': qty})
        else:
            production_move = production._generate_finished_moves()
            production_move = production.move_finished_ids.filtered(lambda x : x.state not in ('done', 'cancel') and production.product_id.id == x.product_id.id)
            production_move.write({'product_uom_qty': qty})

    @api.multi
    def change_prod_qty(self):
        MrpBom = self.env['mrp.bom']
        for wizard in self:
            production = wizard.mo_id
            produced = sum(production.move_finished_ids.mapped('quantity_done'))
            if wizard.product_qty < produced:
                raise UserError(_("You have already produced %d qty , Please give update quantity more then %d ")%(produced, produced))
            production.write({'product_qty': wizard.product_qty})
            #production.action_compute()
            #TODO: Do we still need to change the quantity of a production order?
            production_move = production.move_finished_ids.filtered(lambda x : x.state not in ('done', 'cancel') and production.product_id.id == x.product_id.id)
            for move in production.move_raw_ids:
                bom_point = production.bom_id
                # TDE FIXME: this is not the place to do that kind of computation, please
                if not bom_point:
                    bom_point = MrpBom._bom_find(product=production.product_id, picking_type=production.picking_type_id)
                    if not bom_point:
                        raise UserError(_("Cannot find bill of material for this production."))
                    production.write({'bom_id': bom_point.id})
                if not bom_point:
                    raise UserError(_("Cannot find bill of material for this production."))
                factor = (production.product_qty - production.qty_produced) * production.product_uom_id.factor / bom_point.product_uom_id.factor
                boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
                for line, line_data in lines:
                    production._update_raw_move(line, line_data['qty'])
            self._update_product_to_produce(production, production.product_qty - production.qty_produced)
            moves = production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves.do_unreserve()
            moves.action_assign()
        return {}
