# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class ChangeProductionQty(models.TransientModel):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'

    # TDE FIXME: add production_id field
    product_qty = fields.Float(
        'Product Qty',
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True)

    def default_get(self, fields):
        res = super(ChangeProductionQty, self).default_get(fields)
        if 'product_qty' in fields and not res.get('product_qty'):
            res['product_qty'] = self.env['mrp.production'].browse(self._context['active_id']).product_qty
        return res

    @api.model
    def _update_product_to_produce(self, production, qty):
        production_move = production.move_finished_ids.filtered(lambda x:x.product_id.id == production.product_id.id and x.state not in ('done', 'cancel'))
        if production_move:
            production_move.write({'product_uom_qty': qty})
        else:
            production._make_production_produce_line()
            production_move = production.move_finished_ids.filtered(lambda x : x.state not in ('done', 'cancel') and production.product_id.id == x.product_id.id)
            production_move.write({'product_uom_qty': qty})

    @api.multi
    def change_prod_qty(self):
        record_id = self._context and self._context.get('active_id', False)
        assert record_id, _('Active Id not found')
        MrpBom = self.env['mrp.bom']
        MrpProduction = self.env['mrp.production']
        for wizard_qty in self:
            production = MrpProduction.browse(record_id)
            produced = sum(production.move_finished_ids.mapped('quantity_done'))
            if wizard_qty.product_qty < produced:
                raise UserError(_("You have already produced %d qty , Please give update quantity more then %d ")%(produced, produced))
            production.write({'product_qty': wizard_qty.product_qty})
            #production.action_compute()
            #TODO: Do we still need to change the quantity of a production order?
            production_move = production.move_finished_ids.filtered(lambda x : x.state not in ('done', 'cancel') and production.product_id.id == x.product_id.id)
            for move in production.move_raw_ids:
                bom_point = production.bom_id
                if not bom_point:
                    bom_point = MrpBom._bom_find(product=production.product_id, picking_type=production.picking_type_id)
                    if not bom_point:
                        raise UserError(_("Cannot find bill of material for this production."))
                    production.write({'bom_id': bom_point.id})
                if not bom_point:
                    raise UserError(_("Cannot find bill of material for this production."))
                factor = (production.product_qty - production.qty_produced) * production.product_uom_id.factor / bom_point.product_uom_id.factor
                production.bom_id.explode(production.product_id, factor, method=production._update_move)
            self._update_product_to_produce(production, production.product_qty - production.qty_produced)
            moves = production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves.do_unreserve()
            moves.action_assign()
        return {}
