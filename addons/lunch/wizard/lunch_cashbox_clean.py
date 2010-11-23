# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class lunch_cashbox_clean(osv.osv_memory):

     _name = "lunch.cashbox.clean"
     _description = "clean cashbox"

     def set_to_zero(self, cr, uid, ids, context=None):

         """
         clean Cashbox. set active fields False.
         @param cr: the current row, from the database cursor,
         @param uid: the current user’s ID for security checks,
         @param ids: List  Lunch cashbox Clean’s IDs
         @return:Dictionary {}.
         """
         #TOFIX: use orm methods
         if context is None:
            context = {}
         data = context and context.get('active_ids', []) or []
         cashmove_ref = self.pool.get('lunch.cashmove')
         cr.execute("select user_cashmove, box,sum(amount) from lunch_cashmove \
                 where active = 't' and box IN %s group by user_cashmove, \
                     box"  , (tuple(data),))
         res = cr.fetchall()

         cr.execute("update lunch_cashmove set active = 'f' where active= 't' \
             and box IN %s" , (tuple(data),))
         #TOCHECK: Why need to create duplicate entry after clean box ?
 
         #for (user_id, box_id, amount) in res:
         #   cashmove_ref.create(cr, uid, {
         #       'name': 'Summary for user' + str(user_id),
         #       'amount': amount,
         #       'user_cashmove': user_id,
         #       'box': box_id,
         #       'active': True,
         #   })
         return {}

lunch_cashbox_clean()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

