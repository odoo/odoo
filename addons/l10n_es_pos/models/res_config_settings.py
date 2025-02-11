from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_is_spanish = fields.Boolean(
        string="Consider the specific spanish legislation, such as the use of simplified invoices",
        related="pos_config_id.is_spanish",
    )

    pos_l10n_es_simplified_invoice_limit = fields.Float(
        related="pos_config_id.l10n_es_simplified_invoice_limit",
        readonly=False,
    )
    pos_l10n_es_simplified_invoice_journal_id = fields.Many2one(
        related="pos_config_id.l10n_es_simplified_invoice_journal_id", readonly=False
    )
