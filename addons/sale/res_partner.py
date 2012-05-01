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

from osv import fields,osv
from tools.translate import _

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
        count = dict.fromkeys(ids, 0)
        sale_order_pool=self.pool.get('sale.order')
        sale_order_ids = sale_order_pool.search(cr, uid, [('partner_id', 'in', ids)])
        for sale_order in sale_order_pool.browse(cr, uid, sale_order_ids):
            count[sale_order.partner_id.id] += 1
        return count
    
    _columns = {
        'sale_order_count': fields.function(_sale_order_count , type='integer',string="Sale Order"),
    }
    _defaults = {
        'sale_order_count': 0,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
