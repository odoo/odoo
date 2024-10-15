from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(account.ResCompany, base_vat.ResCompany):

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )
