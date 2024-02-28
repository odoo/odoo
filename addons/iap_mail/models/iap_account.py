# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class IapAccount(models.Model):
    _inherit = 'iap.account'

    @api.model
    def _send_iap_bus_notification(self, service_name, title, error_type=False):
        param = {
            'title': title,
            'error_type': 'danger' if error_type else 'success'
        }
        if error_type == 'credit':
            param['url'] = self.env['iap.account'].get_credits_url(service_name)
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'iap_notification', param)
