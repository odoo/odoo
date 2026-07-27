from odoo import api, fields, models


class GreeceEDIDocument(models.Model):
    _inherit = 'l10n_gr_edi.document'

    picking_id = fields.Many2one(comodel_name='stock.picking', ondelete='cascade')
    state = fields.Selection(
        selection_add=[
            ('delivery_note_sent', "Delivery note sent"),
            ('delivery_note_error', "Delivery note send failed"),
        ],
        ondelete={
            'delivery_note_sent': 'cascade',
            'delivery_note_error': 'cascade',
        },
    )

    @api.model
    def _l10n_gr_edi_get_document_state(self, record, state):
        if record._name == 'stock.picking':
            return 'delivery_note_error' if state == 'error' else 'delivery_note_sent'
        return super()._l10n_gr_edi_get_document_state(record, state)

    @api.model
    def _l10n_gr_edi_get_document_record_vals(self, record):
        if record._name == 'stock.picking':
            return {'picking_id': record.id}
        return super()._l10n_gr_edi_get_document_record_vals(record)

    @api.model
    def _l10n_gr_edi_get_xml_template(self, record):
        if record._name == 'stock.picking':
            return 'l10n_gr_edi.mydata_invoice'
        return super()._l10n_gr_edi_get_xml_template(record)

    @api.model
    def _l10n_gr_edi_get_error_states(self):
        return super()._l10n_gr_edi_get_error_states() | {'delivery_note_error'}
