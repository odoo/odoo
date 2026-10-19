# -*- coding: utf-8 -*-

from . import models


def _assign_default_nomeclature_id(env):
    company_ids_without_default_nomenclature_id  = env['res.company'].search([
        ('nomenclature_id', '=', False)
    ])
    default_nomenclature_id = env.ref('barcodes.default_barcode_nomenclature', raise_if_not_found=False)
    if default_nomenclature_id:
        company_ids_without_default_nomenclature_id.write({
            'nomenclature_id': default_nomenclature_id.id,
        })
