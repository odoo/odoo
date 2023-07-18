# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import Dict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_online_payment_method_id = fields.Many2one('pos.payment.method', string='Online payment method', help="The online payment method to use when a customer pays a self-order online.", domain=[('is_online_payment', '=', True)], compute='_compute_self_order_online_payment_method_id', store=True, readonly=False)

    @api.constrains('self_order_online_payment_method_id')
    def _check_self_order_online_payment_method_id(self):
        if any(config.self_order_online_payment_method_id and not config.self_order_online_payment_method_id._get_online_payment_providers(config.id, error_if_invalid=True) for config in self):
            raise ValidationError(_("The online payment method used for self-order in a POS config must have at least one published payment provider supporting the currency of that POS config."))

    @api.constrains('self_order_table_mode', 'self_order_pay_after', 'self_order_online_payment_method_id')
    def _check_self_order_pay_after_each(self):
        if any(config.self_order_table_mode and config.self_order_pay_after == 'each' and not config.self_order_online_payment_method_id for config in self):
            raise ValidationError(_("The POS self-order mode with payment after each order requires an online payment method to be configured."))

    @api.depends('company_id', 'self_order_table_mode', 'self_order_pay_after', 'self_order_online_payment_method_id')
    def _compute_self_order_online_payment_method_id(self):
        for config in self:
            if not config.self_order_table_mode:
                config.self_order_online_payment_method_id = False
            elif config.self_order_pay_after == 'each' and (not config.self_order_online_payment_method_id or not config.self_order_online_payment_method_id.is_online_payment):
                config.self_order_online_payment_method_id = self.env['pos.payment.method'].sudo()._get_or_create_online_payment_method(config.company_id.id, config.id)

    def _get_self_order_data(self) -> Dict:
        res = super()._get_self_order_data()
        res['has_self_order_online_payment_method'] = bool(self.self_order_online_payment_method_id)
        return res
