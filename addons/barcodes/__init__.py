# -*- coding: utf-8 -*-

from . import models

from .models.barcode_events_mixin import BarcodesBarcode_Events_Mixin
from .models.barcode_nomenclature import BarcodeNomenclature
from .models.barcode_rule import BarcodeRule
from .models.ir_http import IrHttp
from .models.res_company import ResCompany


def _assign_default_nomeclature_id(env):
    company_ids_without_default_nomenclature_id  = env['res.company'].search([
        ('nomenclature_id', '=', False)
    ])
    default_nomenclature_id = env.ref('barcodes.default_barcode_nomenclature', raise_if_not_found=False)
    if default_nomenclature_id:
        company_ids_without_default_nomenclature_id.write({
            'nomenclature_id': default_nomenclature_id.id,
        })
