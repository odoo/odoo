# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class product_template(osv.Model):
    """ Product Template inheritance to add an optional email.template to a
    product.template. When validating an invoice, an email will be send to the
    customer based on this template. The customer will receive an email for each
    product linked to an email template. """
    _inherit = "product.template"

    _columns = {
        'email_template_id': fields.many2one(
            'email.template', 'Product Email Template',
            help='When validating an invoice, an email will be sent to the customer'
                 'based on this template. The customer will receive an email for each'
                 'product linked to an email template.'),
    }
