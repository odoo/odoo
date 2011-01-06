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

from osv import osv, fields

class pos_discount(osv.osv_memory):
    _name = 'pos.discount'
    _description = 'Add Discount'

    _columns = {
        'discount': fields.float('Discount ', required=True),
        'discount_notes': fields.char('Discount Notes', size= 128, required=True),
    }
    _defaults = {
        'discount': 5,
    }


    def view_init(self, cr, uid, fields_list, context=None):
        """
         Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view with new columns.
        """
        if context is None:
            context = {}
        super(pos_discount, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        order = self.pool.get('pos.order').browse(cr, uid, record_id, context=context)
        if not order.lines:
                raise osv.except_osv(_('Error!'), _('No Order Lines'))
        True

    def apply_discount(self, cr, uid, ids, context=None):
        """
         To give the discount of  product and check the.

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return : nothing
        """
        order_ref = self.pool.get('pos.order')
        order_line_ref = self.pool.get('pos.order.line')
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        record_id = context and context.get('active_id', False)
        if isinstance(record_id, (int, long)):
            record_id = [record_id]

        for order in order_ref.browse(cr, uid, record_id, context=context):
            for line in order.lines:
                company_discount = order.company_id.company_discount
                applied_discount = this.discount

                if applied_discount == 0.00:
                    notice = 'No Discount'
                elif company_discount >= applied_discount:
                    notice = 'Minimum Discount'
                else:
                    notice = this.discount_notes
                res_new = {}
                if this.discount <= company_discount:
                    res_new = {
                        'discount': this.discount,
                        'notice': notice,
                        'price_ded': line.price_unit * line.qty * (this.discount or 0) * 0.01 or 0.0
                    }
                else:
                    res_new = {
                        'discount': this.discount,
                        'notice': notice,
                        'price_ded': line.price_unit * line.qty * (this.discount or 0) * 0.01 or 0.0
                    }

                order_line_ref.write(cr, uid, [line.id], res_new, context=context)
        return {}

pos_discount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
