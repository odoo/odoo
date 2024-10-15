from odoo import fields, models
from odoo.addons import account, base_vat


class ResConfigSettings(account.ResConfigSettings, base_vat.ResConfigSettings):

    l10n_es_simplified_invoice_limit = fields.Float(
        related='company_id.l10n_es_simplified_invoice_limit',
        readonly=False,
    )
