# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    """ Product Template inheritance to add an optional email.template to a
    product.template. When validating an invoice, an email will be send to the
    customer based on this template. The customer will receive an email for each
    product linked to an email template. """
    _inherit = "product.template"

    email_template_id = fields.Many2one('mail.template', string='Product Email Template',
        help='When validating an invoice, an email will be sent to the customer '
        'based on this template. The customer will receive an email for each '
        'product linked to an email template.')
