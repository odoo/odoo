# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from typing import Dict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_online_payment_method_id = fields.Many2one('pos.payment.method', string='Self Online Payment', help="The online payment method to use when a customer pays a self-order online.", domain=[('is_online_payment', '=', True)], store=True, readonly=False)

    @api.constrains('self_order_online_payment_method_id')
    def _check_self_order_online_payment_method_id(self):
        for config in self:
            if config.self_ordering_mode == 'mobile' and config.self_ordering_service_mode == 'each' and config.self_order_online_payment_method_id and not config.self_order_online_payment_method_id._get_online_payment_providers(config.id, error_if_invalid=True):
                raise ValidationError(_("The online payment method used for self-order in a POS config must have at least one published payment provider supporting the currency of that POS config."))

    def _get_self_ordering_data(self):
        res = super()._get_self_ordering_data()
        payment_search_params = self.current_session_id._loader_params_pos_payment_method()
        payment_methods = self.self_order_online_payment_method_id.read(payment_search_params['search_params']['fields'])
        res['pos_payment_methods'] += payment_methods
        return res

    def _get_allowed_payment_methods(self):
        if self.self_ordering_mode == 'kiosk':
            return self.payment_method_ids.filtered(lambda p: p.use_payment_terminal in self._ALLOWED_PAYMENT_METHODS or p.is_online_payment)
        else:
            return self.payment_method_ids.filtered(lambda p: p.is_online_payment)
