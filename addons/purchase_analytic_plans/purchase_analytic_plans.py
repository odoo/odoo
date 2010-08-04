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


class purchase_order_line(osv.osv):
    _name='purchase.order.line'
    _inherit='purchase.order.line'
    _columns = {
         'analytics_id':fields.many2one('account.analytic.plan.instance','Analytic Distribution'),
    }

purchase_order_line()

class purchase_order(osv.osv):
    _name='purchase.order'
    _inherit='purchase.order'

    def inv_line_create(self, cr, uid, a, ol):
        res=super(purchase_order,self).inv_line_create(cr, uid, a, ol)
        res[2]['analytics_id']=ol.analytics_id.id
        return res

purchase_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
