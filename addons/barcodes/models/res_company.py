# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_nomenclature(self):
        return self.env.ref('barcodes.default_barcode_nomenclature', raise_if_not_found=False)

    nomenclature_id = fields.Many2one(
        'barcode.nomenclature',
        string="Nomenclature",
        default=_get_default_nomenclature,
    )

    # read on every product search when stock_barcode is installed
    @property
    def _cached_data_fields(self):
        return (*super()._cached_data_fields, 'nomenclature_id')
