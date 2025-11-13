from odoo import fields, models


class L10nTrNilveraEinvoiceExtendedTaxOffice(models.Model):
    _name = "l10n_tr_nilvera_einvoice_extended.tax.office"
    _description = "Turkish Tax Office"
    _translate = False

    name = fields.Char(
        translate=True,
        help="The official name of the Tax Office (e.g., 'Maslak Vergi Dairesi').",
    )
    code = fields.Integer(
        help="The official numeric code for this Tax Office. This is often "
        "required for e-invoice registration and submissions."
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        help="The Turkish province (İl) where this Tax Office is located.",
    )
    state_code = fields.Char(related="state_id.code")
