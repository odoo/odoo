# -*- coding: utf-8 -*-
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


class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'property_valuation_pricelist': fields.property(
            'product.pricelist',
            type='many2one', 
            relation='product.pricelist', 
            domain=[('type','=','valuation')],
            string="Valuation Pricelist", 
            method=True,
            view_load=True,
            help="This pricelist will be used, instead of the default one, \
                    for valuation to the current company"),
    }
    
    def _check_currency(self, cr, uid, ids):
        for rec in self.browse(cr, uid, ids):
            if rec.currency_id.id <> rec.property_valuation_pricelist.currency_id.id:
                return False
        return True
        
    _constraints = [
        (_check_currency, 'Error! You can not chooes a pricelist in a different currency than your company.', ['property_valuation_pricelist'])
    ]

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

