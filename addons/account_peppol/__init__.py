# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import tools

from odoo import api, SUPERUSER_ID
from odoo.tools.sql import column_exists, create_column


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})

    ubl_bis3 = env.ref('account_edi_ubl_cii.ubl_bis3', raise_if_not_found=False)
    if ubl_bis3 and ubl_bis3.name == "Peppol BIS Billing 3.0":
        ubl_bis3.name = "BIS Billing 3.0 (XML)"

    # Create columns `account_peppol_is_endpoint_valid` and `account_peppol_validity_last_check`
    # on 'res.partner' to avoid having them computed by the ORM on installation.
    if not column_exists(cr, 'res_partner', 'account_peppol_is_endpoint_valid'):
        create_column(cr, 'res_partner', 'account_peppol_is_endpoint_valid', 'boolean')
    if not column_exists(cr, 'res_partner', 'account_peppol_validity_last_check'):
        create_column(cr, 'res_partner', 'account_peppol_validity_last_check', 'timestamp')

    # Same for column 'peppol_move_state' on 'account.move'.
    if not column_exists(cr, 'account_move', 'peppol_move_state'):
        create_column(cr, 'account_move', 'peppol_move_state', 'varchar')
