# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_tax_base_account_id = fields.Many2one(
        related='company_id.l10n_account_withholding_tax_base_account_id',
        readonly=False,
    )
