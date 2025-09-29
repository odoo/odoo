# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import tools

from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ubl_bis3 = env.ref('account_edi_ubl_cii.ubl_bis3', raise_if_not_found=False)
    if ubl_bis3 and ubl_bis3.name == "Peppol BIS Billing 3.0":
        ubl_bis3.name = "UBL BIS Billing 3.0"
