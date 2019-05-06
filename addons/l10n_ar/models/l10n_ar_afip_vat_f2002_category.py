from odoo import models, fields


class AfipVatF2002Category(models.Model):

    _name = "l10n_ar.afip.vat.f2002.category"
    _description = "AFIP VAT F2002 Category"

    name = fields.Char(
        required=True,
        index=True,
    )
