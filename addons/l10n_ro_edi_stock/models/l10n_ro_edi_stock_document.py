from odoo import fields, models

DOCUMENT_STATES = [
    ("stock_sent", "Sent"),
    ("stock_sending_failed", "Error"),
    ("stock_validated", "Validated"),
]


class L10nRoEdiStockDocument(models.Model):
    _inherit = "l10n_ro_edi.document"

    invoice_id = fields.Many2one(required=False)
    picking_id = fields.Many2one(comodel_name="stock.picking")

    state = fields.Selection(
        selection_add=DOCUMENT_STATES,
        ondelete={k: "cascade" for k, v in DOCUMENT_STATES},
    )
    message = fields.Char(copy=False)
    l10n_ro_edi_stock_uit = fields.Char(
        copy=False,
        help="UIT of this eTransport document.",
    )
    l10n_ro_edi_stock_load_id = fields.Char(
        copy=False,
        help="Id of this document used for interacting with the anaf api.",
    )
