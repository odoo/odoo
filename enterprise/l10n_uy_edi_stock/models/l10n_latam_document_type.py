from odoo import fields, models


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    internal_type = fields.Selection(selection_add=[("stock_picking", "Delivery Guide")])
