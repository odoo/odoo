from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    extract_bank_statement_digitalization_mode = fields.Selection(
        related='company_id.extract_bank_statement_digitalization_mode',
        string='Bank Statements',
        readonly=False,
    )
