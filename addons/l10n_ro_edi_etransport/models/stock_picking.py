from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Picking(models.Model):
    _inherit = 'stock.picking'

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

        for picking in records.filtered(lambda record: record.company_id.country_id.code == 'RO'):
            if not picking.l10n_ro_edi_etransport_document_id:
                picking.l10n_ro_edi_etransport_document_id = picking.env['l10n_ro.edi.etransport.document'].create({'picking_id': picking.id})
            elif not picking.l10n_ro_edi_etransport_document_id.picking_id or picking.l10n_ro_edi_etransport_document_id.picking_id.id != picking.id:
                picking.l10n_ro_edi_etransport_document_id.picking_id = picking

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

    @api.depends('company_id')
    def _compute_l10n_ro_edi_etransport_should_show(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_should_show = picking.company_id.country_id.code == 'RO'

    @api.depends('company_id', 'state', 'l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_send(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_should_show_send = (picking.l10n_ro_edi_etransport_should_show
                                                               and picking.state == 'done'
                                                               and picking.l10n_ro_edi_etransport_state in ('draft', 'sending_failed'))

    @api.depends('company_id', 'state', 'l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_fetch(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_should_show_fetch = (picking.l10n_ro_edi_etransport_should_show
                                                                and picking.l10n_ro_edi_etransport_state in ('sending', 'amending'))

    @api.depends('l10n_ro_edi_etransport_message')
    def _compute_l10n_ro_edi_etransport_should_show_send_info(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_should_show_send_info = picking.l10n_ro_edi_etransport_message and True

    @api.depends('l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_should_show_amend(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_should_show_amend = (picking.l10n_ro_edi_etransport_should_show
                                                                and picking.l10n_ro_edi_etransport_state in ('sent', 'amending_failed'))

    @api.depends('l10n_ro_edi_etransport_state')
    def _compute_l10n_ro_edi_etransport_fields_readonly(self):
        for picking in self:
            picking.l10n_ro_edi_etransport_fields_readonly = picking.l10n_ro_edi_etransport_state in ('sending', 'amending')

    def button_validate(self):
        # Extends stock.stock_picking
        self._validate_carrier()

        return super().button_validate()

    def _validate_carrier(self):
        validate_carrier = self.env.context.get('l10n_ro_edi_etransport_validate_carrier', False)

        for picking in self.filtered(lambda pick: pick.company_id.country_code == 'RO'
                                     and (pick.l10n_ro_edi_etransport_should_show or validate_carrier)):
            # validate carrier
            if not picking.carrier_id:
                raise UserError(_("The picking %(picking_name)s is missing a delivery carrier.", picking_name=picking.name))

            # validate carrier partner
            if not picking.carrier_id.l10n_ro_edi_etransport_partner_id:
                raise UserError(_("The delivery carrier of %(picking_name)s is missing the partner field value.", picking_name=picking.name))

    def action_l10n_ro_edi_etransport_send_etransport(self):
        self.ensure_one()
        self.l10n_ro_edi_etransport_document_id._send_etransport()

    def action_l10n_ro_edi_etransport_fetch_status(self):
        self.l10n_ro_edi_etransport_document_id._status_request()

    def action_l10n_ro_edi_etransport_amend_etransport(self):
        self.ensure_one()
        self.l10n_ro_edi_etransport_document_id._send_etransport(send_type='amend')
