# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import osv, fields

class product_bom(osv.osv):
    _inherit = 'mrp.bom'
            
    _columns = {
        'standard_price': fields.related('product_tmpl_id','standard_price',type="float",relation="product.product",string="Standard Price",store=False)
    }