# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTag(models.Model):
    _name = 'product.tag'
    _inherit = ['website.multi.mixin', 'product.tag']
