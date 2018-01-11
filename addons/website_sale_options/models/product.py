# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields

class product_template(osv.Model):
    _inherit = "product.template"

    _columns = {
        'optional_product_ids': fields.many2many('product.template','product_optional_rel','src_id','dest_id',string='Optional Products', help="Products to propose when add to cart."),
    }