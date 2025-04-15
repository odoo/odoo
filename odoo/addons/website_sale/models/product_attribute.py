# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    visibility = fields.Selection(
        selection=[('visible', "Visible"), ('hidden', "Hidden")],
        default='visible')
