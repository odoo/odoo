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
    def _update_product_to_produce(self, prod, qty):
        for move in prod.move_created_ids:
            move.write({'product_uom_qty': qty})

    @api.multi
    def change_prod_qty(self):
        production = self.env['mrp.production'].browse(self.env.context['active_id'])
        BoM = self.env['mrp.bom']
        UoM = self.env['product.uom']
        for wizard in self:
            production.write({'product_qty': wizard.product_qty})
            production.action_compute()
            for move in production.move_lines:
                bom = production.bom_id
                if not bom:
                    bom = BoM._bom_find(product_id=production.product_id.id)
                    if not bom:
                        raise UserError(_("Cannot find bill of material for this product."))
                    production.write({'bom_id': bom.id})

                factor = UoM._compute_qty_obj(production.product_uom, production.product_qty, bom.product_uom)
                product_details, workcenter_details = \
                    BoM._bom_explode(bom, production.product_id, factor / bom.product_qty, [])
                for r in product_details:
                    if r['product_id'] == move.product_id.id:
                        move.write({'product_uom_qty': r['product_qty']})
            if production.move_prod_id:
                production.move_prod_id.write({'product_uom_qty' :  wizard.product_qty})
            self._update_product_to_produce(production, wizard.product_qty)
        return {}
