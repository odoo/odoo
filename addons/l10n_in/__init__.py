# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Assign the Indian GST UQC for unprotected UoM(s).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    unprotected_uoms = {
        'uom.product_uom_hour': 'OTH-OTHERS',
        'uom.product_uom_dozen': 'DOZ-DOZENS',
    }
    for uom in unprotected_uoms:
        uom_id = env.ref(uom, raise_if_not_found=False)
        if uom_id:
            uom_id.l10n_in_code = unprotected_uoms[uom]
