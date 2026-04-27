# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ingenico_payment_terminal = fields.Boolean(
        string="Ingenico Payment Terminal",
        config_parameter='pos_iot.ingenico_payment_terminal')
    worldline_payment_terminal = fields.Boolean(
        string="Worldline Payment Terminal",
        config_parameter='pos_iot.worldline_payment_terminal',
        help="The transactions are processed by Worldline. Set your Worldline device on the related payment method.")

    # pos.config fields
    pos_iface_display_id = fields.Many2one(related='pos_config_id.iface_display_id', readonly=False)
    pos_iface_printer_id = fields.Many2one(related='pos_config_id.iface_printer_id', readonly=False)
    pos_iface_scale_id = fields.Many2one(related='pos_config_id.iface_scale_id', readonly=False)
    pos_iface_scanner_ids = fields.Many2many(related='pos_config_id.iface_scanner_ids', readonly=False)

    def set_values(self):
        super().set_values()
        payment_methods = self.env['pos.payment.method'].sudo()
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        if not IrConfigParameter.get_param('pos_iot.ingenico_payment_terminal'):
            payment_methods |= payment_methods.search([('use_payment_terminal', '=', 'ingenico')])
        elif not IrConfigParameter.get_param('pos_iot.worldline_payment_terminal'):
            payment_methods |= payment_methods.search([('use_payment_terminal', '=', 'worldline')])
        if payment_methods:
            payment_methods.write({
                'use_payment_terminal': False,
                'iot_device_id': False
            })
