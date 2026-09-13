from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    l10n_ar_afip_code = fields.Char(
        string="ARCA Code",
        help="This code will be used on electronic invoice",
        size=3,
    )
    l10n_ar_natural_vat = fields.Char(
        string="Natural Person VAT",
        help="Generic VAT number defined by ARCA in order to recognize partners from"
        " this country that are natural persons",
        size=11,
    )
    l10n_ar_legal_entity_vat = fields.Char(
        string="Legal Entity VAT",
        help="Generic VAT number defined by ARCA in order to recognize partners from this"
        " country that are legal entity",
        size=11,
    )
    l10n_ar_other_vat = fields.Char(
        string="Other VAT",
        help="Generic VAT number defined by ARCA in order to recognize partners from this"
        " country that are not natural persons or legal entities",
        size=11,
    )
