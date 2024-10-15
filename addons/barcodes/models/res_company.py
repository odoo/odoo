# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.addons import web


class ResCompany(web.ResCompany):

    def _get_default_nomenclature(self):
        return self.env.ref('barcodes.default_barcode_nomenclature', raise_if_not_found=False)

    nomenclature_id = fields.Many2one(
        'barcode.nomenclature',
        string="Nomenclature",
        default=_get_default_nomenclature,
    )
