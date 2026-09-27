from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_gcc_dual_language_invoice = fields.Boolean(related='company_id.l10n_gcc_dual_language_invoice', readonly=False)
    l10n_gcc_country_is_gcc = fields.Boolean(related='company_id.l10n_gcc_country_is_gcc')
