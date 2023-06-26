# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import demo
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Assign the afip codes for unprotected UoM(s).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    unprotected_uoms = {
        'uom.product_uom_hour': 98,
        'uom.product_uom_dozen': 9,
    }
    for uom in unprotected_uoms:
        uom_id = env.ref(uom, raise_if_not_found=False)
        if uom_id:
            uom_id.l10n_ar_afip_code = unprotected_uoms[uom]
