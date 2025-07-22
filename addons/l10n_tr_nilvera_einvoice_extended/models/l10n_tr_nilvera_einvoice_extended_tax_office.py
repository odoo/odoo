from odoo import fields, models


class L10nTrNilveraEinvoiceExtendedTaxOffice(models.Model):
    _name = "l10n_tr_nilvera_einvoice_extended.tax.office"
    _description = "Turkish Tax Office"
    _translate = False

    name = fields.Char(translate=True)
    code = fields.Integer()
    state_id = fields.Many2one(comodel_name="res.country.state")
    state_code = fields.Char(related="state_id.code")
