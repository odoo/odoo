from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    simplified_journal = fields.Many2one(
        comodel_name="account.journal",
        string="Simplified Journal",
        domain=[("type", "=", "sale")],
        config_parameter="l10n_es_ecommerce.default_simplified_journal_id",
        help="Simplified Journal",
    )
