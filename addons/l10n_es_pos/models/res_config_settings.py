from odoo import fields, models
from odoo.addons import point_of_sale, l10n_es


class ResConfigSettings(point_of_sale.ResConfigSettings, l10n_es.ResConfigSettings):

    pos_l10n_es_simplified_invoice_journal_id = fields.Many2one(
        related="pos_config_id.l10n_es_simplified_invoice_journal_id",
        readonly=False,
    )
