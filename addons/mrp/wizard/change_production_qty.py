# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class ChangeProductionQty(models.TransientModel):
    _name = 'change.production.qty'
    _description = 'Change Quantity of Products'

    product_qty = fields.Float(string='Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)

    @api.model
    def default_get(self, fields):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        res = super(ChangeProductionQty, self).default_get(fields)
        prod = self.env['mrp.production'].browse(self._context.get('active_id'))
        if 'product_qty' in fields:
            res.update({'product_qty': prod.product_qty})
        return res

    def _update_product_to_produce(self, prod, qty):
        for m in prod.move_created_ids:
            m.write({'product_uom_qty': qty})

    @api.multi
    def change_prod_qty(self):
        """
        Changes the Quantity of Product.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        record_id = self._context and self._context.get('active_id', False)
        assert record_id, _('Active Id not found')
        BomObj = self.env['mrp.bom']
        for wiz_qty in self:
            prod = self.env['mrp.production'].browse(record_id)
            prod.write({'product_qty': wiz_qty.product_qty})
            prod.action_compute()

            for move in prod.move_lines:
                bom_point = prod.bom_id
                bom_id = prod.bom_id.id
                if not bom_point:
                    bom_id = BomObj._bom_find(product_id=prod.product_id.id)
                    if not bom_id:
                        raise UserError(_("Cannot find bill of material for this product."))
                    prod.write({'bom_id': bom_id})
                    bom_point = BomObj.browse([bom_id])[0]

                if not bom_id:
                    raise UserError(_("Cannot find bill of material for this product."))

                factor = prod.product_qty * prod.product_uom.factor / bom_point.product_uom.factor
                product_details, workcenter_details = BomObj._bom_explode(bom_point, prod.product_id, factor / bom_point.product_qty, [])
                for r in product_details:
                    if r['product_id'] == move.product_id.id:
                        move.write({'product_uom_qty': r['product_qty']})
            if prod.move_prod_id:
                prod.move_prod_id.write({'product_uom_qty':  wiz_qty.product_qty})
            self._update_product_to_produce(prod, wiz_qty.product_qty)
        return {}
