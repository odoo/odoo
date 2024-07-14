# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    payment_terminal_ids = fields.Many2many('iot.device', compute="_compute_payment_terminal_ids")
    iot_device_id = fields.Many2one('iot.device', string='Payment Terminal Device')

    def _get_payment_terminal_selection(self):
        selection_list = super(PoSPaymentMethod, self)._get_payment_terminal_selection()
        if self.env['ir.config_parameter'].sudo().get_param('pos_iot.ingenico_payment_terminal'):
            selection_list.append(('ingenico', 'Ingenico'))
        if self.env['ir.config_parameter'].sudo().get_param('pos_iot.worldline_payment_terminal'):
            selection_list.append(('worldline', 'Worldline'))
        return selection_list

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super(PoSPaymentMethod, self)._onchange_use_payment_terminal()
        self.iot_device_id = False

    @api.depends('use_payment_terminal')
    def _compute_payment_terminal_ids(self):
        for payment_method in self:
            domain = [('type', '=', 'payment')]
            if payment_method.use_payment_terminal == 'ingenico':
                domain.append(('manufacturer', '=', 'Ingenico'))
            elif payment_method.use_payment_terminal == 'worldline':
                domain.append(('manufacturer', '=', 'Worldline'))
            elif payment_method.use_payment_terminal == 'six_iot':
                domain.append(('manufacturer', '=', 'Six'))
            payment_method.payment_terminal_ids = self.env['iot.device'].search(domain)
