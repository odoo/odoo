# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    multi_uom_price_id = fields.One2many('product.multi.uom.price', 'product_id', _("UOM price"))
