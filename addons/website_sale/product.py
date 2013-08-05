# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class product_pricelist(osv.osv):
    _inherit = "product.product"
    _columns = {
        'website_published': fields.boolean('Available in the website'),
    }