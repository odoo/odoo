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

from osv import osv,fields

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'po_lead': fields.float('Purchase Lead Time', required=True,
            help="This is the leads/security time for each purchase order."),
    }
    _defaults = {
        'po_lead': lambda *a: 1.0,
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(company, self).write(cr, uid, ids, vals, context)
        product_pricelist_obj = self.pool.get('product.pricelist')
        currency = product_pricelist_obj._get_currency(cr, uid, context)
        pricelist = self.pool.get('ir.model.data').get_object(cr, uid, 'purchase', 'list0')
        product_pricelist_obj.write(cr, uid, pricelist.id, {'currency_id': currency}, context=context)
        return res
    
company()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
