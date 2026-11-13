from odoo import fields, models


class L10nAzEqfErrorWizard(models.TransientModel):
    _name = 'l10n_az.eqf.error.wizard'
    _description = "EQF Generation Errors"

    alerts = fields.Json(readonly=True)
