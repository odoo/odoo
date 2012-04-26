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
    
    def _total_sale(self, cr, uid, ids, field_name, arg, context=None):
        total_sale={}
        sale_pool=self.pool.get('sale.order')
        for id in ids:
            sale_ids = sale_pool.search(cr, uid, [('partner_id', '=', id)])
            total_sale[id] = len(sale_ids)
        return total_sale
    
    _columns = {
        'total_sale': fields.function(_total_sale , type='integer',string="Total Sale"),
    }
    _defaults = {
        'total_sale': 0,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
