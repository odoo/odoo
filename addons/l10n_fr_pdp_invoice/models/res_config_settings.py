from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_pdp_late_payment_penalties_applicable = fields.Boolean(
        related='company_id.l10n_fr_pdp_late_payment_penalties_applicable',
    )
    l10n_fr_pdp_late_payment_penalties_rate = fields.Float(
        related='company_id.l10n_fr_pdp_late_payment_penalties_rate',
        readonly=False,
    )
    l10n_fr_pdp_late_payment_penalties_automatic = fields.Boolean(
        related='company_id.l10n_fr_pdp_late_payment_penalties_automatic',
        readonly=False,
    )
    l10n_fr_pdp_late_payment_penalties_period = fields.Date(
        related='company_id.l10n_fr_pdp_late_payment_penalties_period',
    )
