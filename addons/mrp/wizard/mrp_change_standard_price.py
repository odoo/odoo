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

from osv import fields, osv

class change_standard_price(osv.osv_memory):
    _inherit = "stock.change.standard.price"
    _description = "Change Standard Price"
    
    _columns = {
        'change_parent_price': fields.boolean('Change Parent Price', help="This will change the price of parent products also "
                                              "according to the BoM structure specified for the product."),
    }
    
    
    def change_price(self, cr, uid, ids, context=None):
        """ Changes the Standard Price of Parent Product according to BoM 
            only when the field 'change_parent_price' is True.
            And creates an account move accordingly.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        res = self.browse(cr, uid, ids, context=context) 
        context.update({'change_parent_price': res[0].change_parent_price})
        return super(change_standard_price, self).change_price(cr, uid, ids, context=context)
    
change_standard_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
