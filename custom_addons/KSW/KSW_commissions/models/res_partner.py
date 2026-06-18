"""Extends res.partner with commission import fields.

``x_commission_account_number`` — the account number exactly as it
appears in the accountant's Excel sales file (col 0).  This is the
most reliable matching key because account numbers are stable identifiers
that don't change when customer names are updated.

``x_commission_import_name`` — name alias fallback for cases where the
account number is unavailable or not yet filled in.
"""
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_client_account_number = fields.Char(
        string='Client Account Number',
        help='Account number exactly as it appears in col 0 of the '
             'accountant\'s monthly Sales Excel file. '
             'Used by the import wizard as the primary key to match '
             'this customer to the correct commission split bucket. '
             'Takes priority over the Commission Import Name.',
    )
    x_commission_import_name = fields.Char(
        string='Commission Import Name',
        help='Customer name exactly as it appears in the accountant\'s '
             'monthly Sales Excel file (col 1 = Customer name). '
             'Fallback when Commission Account Number is blank. '
             'Leave blank to fall back to the partner\'s regular Name.',
    )



