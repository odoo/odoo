from odoo.addons.l10n_ro_edi_stock.models.etransport_api import ETransportAPI
from odoo import api, fields, models, _

DOCUMENT_STATES = [
    ('stock_sent', "Sent"),
    ('stock_sending_failed', "Error"),
    ('stock_validated', 'Validated'),
]


class L10nRoEdiStockDocument(models.Model):
    _inherit = 'l10n_ro_edi.document'

    invoice_id = fields.Many2one(required=False)
    picking_id = fields.Many2one(comodel_name='stock.picking')

    state = fields.Selection(selection_add=DOCUMENT_STATES, ondelete={k: 'cascade' for k, v in DOCUMENT_STATES})
    message = fields.Char(string="Message", copy=False)
    l10n_ro_edi_stock_uit = fields.Char(help="UIT of this eTransport document.", copy=False)
    l10n_ro_edi_stock_load_id = fields.Char(help="Id of this document used for interacting with the anaf api.", copy=False)

    @api.model
    def _l10n_ro_edi_stock_fetch_etransport_document(self, company, load_id, session):
        return ETransportAPI._make_etransport_request(
            company=company,
            endpoint=f'stareMesaj/{load_id}',
            method='get',
            session=session,
        )
