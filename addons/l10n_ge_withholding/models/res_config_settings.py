from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ge_withholding_gross_account_id = fields.Many2one(related='company_id.l10n_ge_withholding_gross_account_id', readonly=False)
