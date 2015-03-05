# -*- coding: utf-8 -*-
from openerp import models, fields


class ProductTemplate(models.Model):
    _inherit = ['product.template']

    digital_content = fields.Boolean(help="If checked, it will allow clients to download the product attachments when they have bought it.")
