from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_l10n_es_tbai_is_required = fields.Boolean(
        string="TicketBAI required",
        related="company_id.l10n_es_tbai_is_required",
    )
    pos_l10n_es_tbai_simplified_invoice_limit = fields.Float(
        related="pos_config_id.l10n_es_tbai_simplified_invoice_limit",
        readonly=False,
    )
