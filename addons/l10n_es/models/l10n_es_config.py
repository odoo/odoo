from odoo import fields, models


class L10nEsConfig(models.Model):
    _name = "l10n_es.config"
    _description = "A company's l10n es configuration"
    _inherit = ["mixin.company.config"]

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        default=400,
        help="Over this amount is not legally possible to create a simplified invoice",
    )
