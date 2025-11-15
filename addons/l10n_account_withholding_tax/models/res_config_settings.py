# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_journal_id = fields.Many2one(
        related='company_id.withholding_journal_id',
        readonly=False,
    )
    withholding_tax_control_account_id = fields.Many2one(
        related='company_id.withholding_tax_control_account_id',
        readonly=False,
    )
