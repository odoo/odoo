# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # gelato_reference = fields.Char(name="Gelato ProductUID"),
    # attachment_link = fields.Char(name="Attachement link")
