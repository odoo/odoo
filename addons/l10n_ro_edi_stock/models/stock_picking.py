from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_ro_edi_stock_interface_id = fields.Many2one(
        comodel_name='l10n_ro.edi.stock.etransport.interface',
        delegate=True,
        ondelete='cascade',
        default=None,
    )

    l10n_ro_edi_stock_enable = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable')
    l10n_ro_edi_stock_enable_send = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_send')
    l10n_ro_edi_stock_enable_fetch = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_fetch')
    l10n_ro_edi_stock_enable_send_info = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_send_info')
    l10n_ro_edi_stock_enable_amend = fields.Boolean(compute='_compute_l10n_ro_edi_stock_enable_amend')

    l10n_ro_edi_stock_fields_readonly = fields.Boolean(compute='_compute_l10n_ro_edi_stock_fields_readonly')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for picking in records.filtered(lambda record: record.company_id.country_id.code == 'RO'):
            if not picking.l10n_ro_edi_stock_interface_id:
                picking.l10n_ro_edi_stock_interface_id = picking.env['l10n_ro.edi.stock.etransport.interface'].create({'picking_id': picking.id})
            elif not picking.l10n_ro_edi_stock_interface_id.picking_id or picking.l10n_ro_edi_stock_interface_id.picking_id.id != picking.id:
                picking.l10n_ro_edi_stock_interface_id.picking_id = picking

        return records

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}

        if self.l10n_ro_edi_stock_interface_id:
            copy_data = self.l10n_ro_edi_stock_interface_id.copy_data()[0]
            interface_copy = self.env['l10n_ro.edi.stock.etransport.interface'].create(copy_data)
            default['l10n_ro_edi_stock_interface_id'] = interface_copy.id

        return super().copy_data(default)

    @api.onchange('l10n_ro_edi_stock_operation_type')
    def _reset_location_type(self):
        self.l10n_ro_edi_stock_interface_id._reset_location_type()

    @api.onchange('l10n_ro_edi_stock_operation_type', 'l10n_ro_edi_stock_start_loc_type')
    def _reset_start_location_data(self):
        self.l10n_ro_edi_stock_interface_id._reset_location_data('start')

    @api.onchange('l10n_ro_edi_stock_operation_type', 'l10n_ro_edi_stock_end_loc_type')
    def _reset_end_location_data(self):
        self.l10n_ro_edi_stock_interface_id._reset_location_data('end')

    @api.depends('company_id.country_code')
    def _compute_l10n_ro_edi_stock_enable(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable = picking.company_id.country_code == 'RO'

    @api.depends('l10n_ro_edi_stock_enable', 'state', 'l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_send(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_send = (picking.l10n_ro_edi_stock_enable
                                                     and picking.state == 'done'
                                                     and picking.l10n_ro_edi_stock_state in (False, 'etransport_sending_failed')
                                                     and not picking.l10n_ro_edi_stock_interface_id._get_last_etransport_sent_document())

    @api.depends('company_id', 'state', 'l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_fetch(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_fetch = picking.l10n_ro_edi_stock_enable and picking.l10n_ro_edi_stock_state == 'etransport_sending'

    @api.depends('l10n_ro_edi_stock_document_message')
    def _compute_l10n_ro_edi_stock_enable_send_info(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_send_info = bool(picking.l10n_ro_edi_stock_document_message)

    @api.depends('l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_enable_amend(self):
        for picking in self:
            picking.l10n_ro_edi_stock_enable_amend = picking.l10n_ro_edi_stock_enable and (picking.l10n_ro_edi_stock_state == 'etransport_sent'
                                                                                           or (picking.l10n_ro_edi_stock_state == 'etransport_sending_failed'
                                                                                               and picking.l10n_ro_edi_stock_interface_id._get_last_etransport_sent_document()))

    @api.depends('l10n_ro_edi_stock_state')
    def _compute_l10n_ro_edi_stock_fields_readonly(self):
        for picking in self:
            picking.l10n_ro_edi_stock_fields_readonly = picking.l10n_ro_edi_stock_state == 'etransport_sending'

    def button_validate(self):
        # Extends stock.stock_picking
        self._validate_carrier()

        return super().button_validate()

    def _validate_carrier(self):
        validate_carrier = self.env.context.get('l10n_ro_edi_stock_validate_carrier', False)

        for picking in self.filtered(lambda pick: pick.company_id.country_code == 'RO' and (pick.l10n_ro_edi_stock_enable or validate_carrier)):
            # validate carrier
            if not picking.carrier_id:
                raise UserError(_("The picking %(picking_name)s is missing a delivery carrier.", picking_name=picking.name))

            # validate carrier partner
            if not picking.carrier_id.l10n_ro_edi_stock_partner_id:
                raise UserError(_("The delivery carrier of %(picking_name)s is missing the partner field value.", picking_name=picking.name))

    def action_l10n_ro_edi_stock_send_etransport(self):
        self.ensure_one()

        send_type = self.env.context.get('l10n_ro_edi_stock_send_type', 'send')
        self.l10n_ro_edi_stock_interface_id._send_etransport_document(send_type=send_type)

    def action_l10n_ro_edi_stock_fetch_status(self):
        self.l10n_ro_edi_stock_interface_id._fetch_document_status()
