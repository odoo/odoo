# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'email_template_id': fields.many2one('email.template','Product Email Template'),
    }
