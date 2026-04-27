# coding: utf-8
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_cl_delivery_guide_price = fields.Selection([
        ('product', 'From Product'),
        ('sale_order', 'From Sale Order'),
        ('none', 'Do Not Show Price')
    ], string='Delivery Guide Price', default='sale_order', help="Chile: Select which price of the product will be shown in the delivery guide, if any.")
