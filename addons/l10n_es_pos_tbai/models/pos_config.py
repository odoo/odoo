from odoo import fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_es_tbai_simplified_invoice_limit = fields.Float(
        string="TicketBAI Simplified Invoice limit amount",
        help="Over this amount, it is not legally possible to create a simplified invoice",
        default=400,
    )
