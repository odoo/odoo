from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_eg_dual_language_invoice = fields.Boolean(related='company_id.l10n_eg_dual_language_invoice', readonly=False)
