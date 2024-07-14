# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_at_oenace_code = fields.Char(
        related='company_id.l10n_at_oenace_code',
        readonly=False,
    )

    l10n_at_profit_assessment_method = fields.Selection(
        related='company_id.l10n_at_profit_assessment_method',
        readonly=False,
    )
