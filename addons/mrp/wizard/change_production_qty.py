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
        production = self.env['mrp.production'].browse(self._context.get('active_id'))
        if 'product_qty' in fields:
            res.update({'product_qty': production.product_qty})
        return res

    def _update_product_to_produce(self, production, qty):
        for move in production.move_created_ids:
            move.write({'product_uom_qty': qty})

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
        MrpBom = self.env['mrp.bom']
        for wizard_qty in self:
            production = self.env['mrp.production'].browse(record_id)
            production.write({'product_qty': wizard_qty.product_qty})
            production.action_compute()

            for move in production.move_line_ids:
                bom_point = production.bom_id
                bom_id = production.bom_id.id
                if not bom_point:
                    bom_id = MrpBom._bom_find(product_id=production.product_id.id)
                    if not bom_id:
                        raise UserError(_("Cannot find bill of material for this production."))
                    production.write({'bom_id': bom_id})
                    bom_point = MrpBom.browse([bom_id])[0]

                if not bom_id:
                    raise UserError(_("Cannot find bill of material for this production."))

                factor = production.product_qty * production.product_uom_id.factor / bom_point.product_uom_id.factor
                product_details, workcenter_details = MrpBom._bom_explode(bom_point, production.product_id, factor / bom_point.product_qty, [])
                for r in product_details:
                    if r['product_id'] == move.product_id.id:
                        move.write({'product_uom_qty': r['product_qty']})
            if production.move_prod_id:
                production.move_prod_id.write({'product_uom_qty':  wizard_qty.product_qty})
            self._update_product_to_produce(production, wizard_qty.product_qty)
        return {}
