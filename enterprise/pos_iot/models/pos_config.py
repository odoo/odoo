# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_print_via_proxy = fields.Boolean(compute="_compute_print_via_proxy")
    iface_printer_id = fields.Many2one('iot.device', domain=lambda self: ['&', ('type', '=', 'printer'), ('subtype', '=', 'receipt_printer'), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)])
    iface_display_id = fields.Many2one('iot.device', domain=lambda self: [('type', '=', 'display'), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)])
    iface_scan_via_proxy = fields.Boolean(compute="_compute_scan_via_proxy")
    iface_scanner_ids = fields.Many2many('iot.device', domain=lambda self: [('type', '=', 'scanner'), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)],
                                         help="Enable barcode scanning with a remotely connected barcode scanner and card swiping with a Vantiv card reader.")
    iface_electronic_scale = fields.Boolean(compute="_compute_electronic_scale")
    iface_scale_id = fields.Many2one('iot.device', domain=lambda self: [('type', '=', 'scale'), '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)])
    iot_device_ids = fields.Many2many('iot.device', compute="_compute_iot_device_ids")
    # TODO: Remove this field, it's not being used.
    payment_terminal_device_ids = fields.Many2many('iot.device', compute="_compute_payment_terminal_device_ids")

    @api.depends('iface_printer_id')
    def _compute_print_via_proxy(self):
        for config in self:
            config.iface_print_via_proxy = config.iface_printer_id.id is not False

    @api.depends('iface_scanner_ids')
    def _compute_scan_via_proxy(self):
        for config in self:
            config.iface_scan_via_proxy = len(config.iface_scanner_ids)

    @api.depends('iface_scale_id')
    def _compute_electronic_scale(self):
        for config in self:
            config.iface_electronic_scale = config.iface_scale_id.id is not False

    @api.depends('iface_printer_id', 'iface_display_id', 'iface_scanner_ids', 'iface_scale_id')
    def _compute_iot_device_ids(self):
        for config in self:
            if config.is_posbox:
                config.iot_device_ids = config.iface_printer_id + config.iface_display_id + config.iface_scanner_ids + config.iface_scale_id
            else:
                config.iot_device_ids = False

    @api.depends('payment_method_ids', 'payment_method_ids.iot_device_id')
    def _compute_payment_terminal_device_ids(self):
        for config in self:
            config.payment_terminal_device_ids = config.payment_method_ids.mapped('iot_device_id')

    def _get_display_device_ip(self):
        if self.iface_display_id:
            return self.iface_display_id.iot_ip
        else:
            return super()._get_display_device_ip()

    @api.constrains('iface_display_id', 'customer_display_type', 'is_posbox')
    def _check_customer_display_type(self):
        for config in self:
            if config.customer_display_type == 'proxy' and (not config.is_posbox or not config.iface_display_id):
                raise UserError(_("You must set a display device for an IOT-connected screen. You'll find the field under the 'IoT Box' option."))
