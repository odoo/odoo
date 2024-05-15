from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    l10n_ro_edi_etransport_document_id = fields.Many2one(comodel_name='l10n_ro.edi.etransport.document', delegate=True, ondelete='cascade', default=None)

    l10n_ro_edi_etransport_should_show = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_should_show')
    l10n_ro_edi_etransport_should_show_send = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_should_show_send')
    l10n_ro_edi_etransport_should_show_fetch = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_should_show_fetch')
    l10n_ro_edi_etransport_should_show_send_info = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_should_show_send_info')
    l10n_ro_edi_etransport_should_show_amend = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_should_show_amend')

    l10n_ro_edi_etransport_fields_readonly = fields.Boolean(compute='_compute_l10n_ro_edi_etransport_fields_readonly')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for batch in records.filtered(lambda record: record.company_id.country_id.code == 'RO'):
            if not batch.l10n_ro_edi_etransport_document_id:
                batch.l10n_ro_edi_etransport_document_id = batch.env['l10n_ro.edi.etransport.document'].create({'batch_id': batch.id})
            elif not batch.l10n_ro_edi_etransport_document_id.batch_id or batch.l10n_ro_edi_etransport_document_id.batch_id.id != batch.id:
                batch.l10n_ro_edi_etransport_document_id.batch_id = batch

        return records

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}

        if self.l10n_ro_edi_etransport_document_id:
            copy_data = self.l10n_ro_edi_etransport_document_id.copy_data()[0]
            document_copy = self.env['l10n_ro.edi.etransport.document'].create(copy_data)
            default['l10n_ro_edi_etransport_document_id'] = document_copy.id

        return super().copy_data(default)

    @api.onchange('l10n_ro_edi_etransport_operation_type_id')
    def _reset_location_type(self):
        self.l10n_ro_edi_etransport_document_id._reset_location_type()

    @api.onchange('l10n_ro_edi_etransport_operation_type_id', 'l10n_ro_edi_etransport_start_loc_type_1', 'l10n_ro_edi_etransport_start_loc_type_2')
    def _reset_start_location_data(self):
        self.l10n_ro_edi_etransport_document_id._reset_location_data('start')

    @api.onchange('l10n_ro_edi_etransport_operation_type_id', 'l10n_ro_edi_etransport_end_loc_type_1', 'l10n_ro_edi_etransport_end_loc_type_2')
    def _reset_end_location_data(self):
        self.l10n_ro_edi_etransport_document_id._reset_location_data('end')

    @api.depends('company_id.country_id')
    def _compute_l10n_ro_edi_etransport_should_show(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_should_show = batch.company_id.country_id.code == 'RO'

    @api.depends('l10n_ro_edi_etransport_should_show', 'state', 'l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_send(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_should_show_send = (batch.l10n_ro_edi_etransport_should_show
                                                             and batch.state != 'draft'
                                                             and batch.l10n_ro_edi_etransport_state in ('draft', 'sending_failed'))

    @api.depends('l10n_ro_edi_etransport_should_show', 'state', 'l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_fetch(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_should_show_fetch = (batch.l10n_ro_edi_etransport_should_show
                                                              and batch.l10n_ro_edi_etransport_state in ('sending', 'amending'))

    @api.depends('l10n_ro_edi_etransport_message')
    def _compute_l10n_ro_edi_etransport_should_show_send_info(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_should_show_send_info = batch.l10n_ro_edi_etransport_message and True

    @api.depends('l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_amend(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_should_show_amend = (batch.l10n_ro_edi_etransport_should_show
                                                              and batch.l10n_ro_edi_etransport_state in ('sent', 'amending_failed'))

    @api.depends('l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_fields_readonly(self):
        for batch in self:
            batch.l10n_ro_edi_etransport_fields_readonly = batch.l10n_ro_edi_etransport_state in ('sending', 'amending')

    def action_done(self):
        # Extends stock_picking_batch
        self.ensure_one()
        self._check_company()

        self.picking_ids.with_context(l10n_ro_edi_etransport_validate_carrier=True)._validate_carrier()

        # Carrier should be the same on all pickings
        first_carrier = self.picking_ids[0].carrier_id
        if any(picking.carrier_id != first_carrier for picking in self.picking_ids):
            raise UserError(_("All Pickings in a Batch Transfer should have the same Carrier"))

        # Commercial partner should be the same on all pickings
        first_commercial_partner = self.picking_ids[0].partner_id.commercial_partner_id
        if any(picking.partner_id.commercial_partner_id != first_commercial_partner for picking in self.picking_ids):
            raise UserError(_("All Pickings in a Batch Transfer should have the same Commercial Partner"))

        return super().action_done()

    def action_l10n_ro_edi_etransport_send_etransport(self):
        self.ensure_one()
        self.l10n_ro_edi_etransport_document_id._send_etransport()

    def action_l10n_ro_edi_etransport_fetch_status(self):
        self.l10n_ro_edi_etransport_document_id._status_request()

    def action_l10n_ro_edi_etransport_amend_etransport(self):
        self.ensure_one()
        self.l10n_ro_edi_etransport_document_id._send_etransport(send_type='amend')
