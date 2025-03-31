from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_l10n_es_simplified_invoice_journal_id = fields.Many2one(
        related="pos_config_id.l10n_es_simplified_invoice_journal_id",
        readonly=False,
    )
