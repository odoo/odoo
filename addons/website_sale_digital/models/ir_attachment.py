# -*- encoding: utf-8 -*-
from openerp import models, fields, api, _


class ir_attachment(models.Model):
    _inherit = ['ir.attachment']

    product_downloadable = fields.Boolean("Downloadable from product portal", default=False)
