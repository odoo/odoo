# -*- coding: utf-8 -*-

from . import models

from odoo import api, SUPERUSER_ID


def _assign_default_nomeclature_id(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids_without_default_nomenclature_id  = env['res.company'].search([
        ('nomenclature_id', '=', False)
    ])
    default_nomenclature_id = env.ref('barcodes.default_barcode_nomenclature', raise_if_not_found=False)
    if default_nomenclature_id:
        company_ids_without_default_nomenclature_id.write({
            'nomenclature_id': default_nomenclature_id.id,
        })
