# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError

import openerp.addons.decimal_precision as dp


class ChangeDisassembleQty(models.TransientModel):
    _name = 'change.disassemble.qty'
    _description = 'Change Quantity for Disassemble Products'

    product_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)

    @api.model
    def default_get(self, fields):
        res = super(ChangeDisassembleQty, self).default_get(fields)
        prod = self.env['mrp.production'].browse(self.env.context.get('active_id', []))
        if 'product_qty' in fields:
            res.update({'product_qty': prod.qty_to_disassemble * -1})
        return res

    @api.multi
    def change_disassemble_qty(self):
        self.ensure_one()
        mrp_production_obj = self.env['mrp.production']
        qty = self.product_qty
        if qty >= 0:
            raise UserError(_('Quantity must be negative to disassemble.'))
        mrp_record = mrp_production_obj.browse(self.env.context.get('active_id', []))
        if mrp_record.qty_to_disassemble < abs(qty):
            raise UserError(_('You are going to disassemble total %s quantities of "%s".\nBut you can only disassemble up to total %s quantities.') % (abs(qty), mrp_record.product_id.name, mrp_record.qty_to_disassemble))
        mrp_record.write({'qty_to_disassemble': mrp_record.qty_to_disassemble - abs(qty)})
        return mrp_record.action_disassemble(qty)
