from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ar_arca_activity_id = fields.Many2one(
        'l10n_ar.arca.activity',
        related='company_id.l10n_ar_arca_activity_id', readonly=False)
