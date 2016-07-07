# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

class product_template(osv.Model):
    _inherit = "product.template"

    _columns = {
        'website_description': fields.html('Description for the website'), # hack, if website_sale is not installed
        'quote_description': fields.html('Description for the quote'),
    }
