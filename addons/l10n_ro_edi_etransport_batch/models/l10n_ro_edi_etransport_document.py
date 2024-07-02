from odoo import api, fields, models, _


class L10nRoEdiETransportDocument(models.Model):
    _inherit = 'l10n_ro.edi.etransport.document'

    batch_id = fields.Many2one(comodel_name='stock.picking.batch', default=None)

    @api.depends('picking_id.company_id', 'batch_id.company_id')
    def _compute_l10n_ro_edi_etransport_company_id(self):
        # Extends l10n_ro_edi_etransport
        for doc in self:
            doc.l10n_ro_edi_etransport_company_id = (doc.batch_id or doc.picking_id).company_id

    @api.depends('picking_id.move_ids', 'batch_id.move_ids')
    def _compute_l10n_ro_edi_etransport_move_ids(self):
        # Extends l10n_ro_edi_etransport
        for doc in self:
            doc.l10n_ro_edi_etransport_move_ids = (doc.batch_id or doc.picking_id).move_ids

    @api.depends('picking_id.carrier_id', 'batch_id.picking_ids')
    def _compute_l10n_ro_edi_etransport_carrier_id(self):
        # Extends l10n_ro_edi_etransport
        for doc in self:
            if doc.batch_id:
                doc.l10n_ro_edi_etransport_carrier_id = doc.batch_id.picking_ids[0].carrier_id if doc.batch_id.picking_ids else None
            else:
                doc.l10n_ro_edi_etransport_carrier_id = doc.picking_id.carrier_id

    def _get_declarant_ref(self) -> str:
        # Extends l10n_ro_edi_etransport
        self.ensure_one()
        return self.batch_id.name if self.batch_id else super()._get_declarant_ref()

    def _get_scheduled_date(self):
        # Extends l10n_ro_edi_etransport
        self.ensure_one()
        return self.batch_id.scheduled_date.date() if self.batch_id else super()._get_scheduled_date()

    def _get_commercial_partner(self):
        # Extends l10n_ro_edi_etransport
        self.ensure_one()
        return self.batch_id.picking_ids[0].partner_id.commercial_partner_id if self.batch_id else super()._get_commercial_partner()

    def _get_transport_partner(self):
        # Extends l10n_ro_edi_etransport
        self.ensure_one()
        return self.batch_id.picking_ids[0].carrier_id.l10n_ro_edi_etransport_partner_id if self.batch_id else super()._get_transport_partner()

    def _report_unhandled_document_state(self, state: str):
        # Extends l10n_ro_edi_etransport
        self.ensure_one()
        (self.batch_id or self.picking_id).message_post(body=_("Unhandled eTransport document state: %(state)s", state=state))
