# -*- coding: utf-8 -*-

from odoo import models, api


class UoM(models.Model):
    _inherit = 'uom.uom'

    @api.model
    def _get_fields_stock_barcode(self):
        return [
            'name',
            'category_id',
            'factor',
            'rounding',
        ]
