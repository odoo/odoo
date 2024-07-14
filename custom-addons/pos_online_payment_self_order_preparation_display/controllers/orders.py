# -*- coding: utf-8 -*-

from odoo.addons.pos_self_order_preparation_display.controllers.orders import PosSelfOrderPreparationDisplayController

class PosOnlineSelfOrderPreparationDisplayController(PosSelfOrderPreparationDisplayController):
    def _get_self_payment_methods(self, pos_config):
        payment_methods = super()._get_self_payment_methods(pos_config)
        if pos_config.self_ordering_mode == 'mobile':
            payment_methods = pos_config.self_order_online_payment_method_id
        return payment_methods
