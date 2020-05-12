# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class IapAccount(models.Model):
    _inherit = 'iap.account'

    def _get_brand_name_from_service_name(self, service_name):
        if service_name == 'snailmail':
            return _('Snailmail')
        if service_name == 'sms':
            return _('SMS')
        return super(IapAccount, self)._get_brand_name_from_service_name(service_name)
