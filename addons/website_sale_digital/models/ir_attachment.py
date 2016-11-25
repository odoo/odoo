# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Attachment(models.Model):

    _inherit = 'ir.attachment'

    product_downloadable = fields.Boolean("Downloadable from product portal", default=False)
    download_count = fields.Integer(string="No. of downloads", help="Numbers of downloads as digital product", default=0)
