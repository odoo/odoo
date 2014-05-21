# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class change_disassemble_qty(osv.osv_memory):
    _name = 'change.disassemble.qty'
    _description = 'Change Quantity for Disassemble Products'

    _columns = {
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        res = super(change_disassemble_qty, self).default_get(cr, uid, fields, context=context)
        prod = self.pool.get('mrp.production').browse(cr, uid, context.get('active_id'), context=context)
        if 'product_qty' in fields:
            res.update({'product_qty': prod.qty_to_disassemble * -1 })
        return res

    def change_disassemble_qty(self, cr, uid, ids, context=None):
        mrp_production_obj = self.pool.get('mrp.production')
        mrp_id = context.get('active_id', False)
        qty = self.browse(cr, uid, ids[0], context=context).product_qty
        if qty >= 0:
            raise osv.except_osv(_('Warning!'), _('Quantity must be negative to disassemble.'))
        mrp_record = mrp_production_obj.browse(cr, uid, mrp_id, context=context)
        mrp_record.write({'qty_to_disassemble': mrp_record.qty_to_disassemble - abs(qty)}, context=context)
        if mrp_record.qty_to_disassemble < abs(qty) :
            raise osv.except_osv(_('Warning!'), _('You are going to disassemble total %s quantities of "%s".\nBut you can only disassemble up to total %s quantities.') % (abs(qty), mrp_record.product_id.name, mrp_record.qty_to_disassemble))
        return mrp_production_obj.action_disassemble(cr, uid, mrp_id, qty, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: