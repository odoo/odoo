from odoo import models, fields


class L10nTrAccountTaxCode(models.Model):
    _name = "l10n_tr.res.tax.office"
    _description = "Turkish Tax Offices"
    _translate = False

    name = fields.Char(translate=True)
    code = fields.Integer()
    state_id = fields.Many2one("res.country.state")
    state_code = fields.Char(related="state_id.code")
