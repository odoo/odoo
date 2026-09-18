from . import models

from odoo.exceptions import UserError
from odoo.tools.translate import _


def _pre_init_check_conflict(env):
    if env['ir.module.module']._get('account_cleartax_ae').state == 'installed':
        raise UserError(_(
            "'UAE - UBL PINT on Peppol' cannot be installed alongside 'ClearTax - United Arab "
            "Emirates' (account_cleartax_ae): both send the same PINT AE documents over a "
            "different network, and installing both would offer two routes for every invoice."
        ))
