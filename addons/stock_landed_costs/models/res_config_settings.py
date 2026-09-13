from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lc_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.lc_journal_id",
        string="Default Journal",
        readonly=False,
    )
