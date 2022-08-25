# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IapAccount(models.Model):
    _inherit = 'iap.account'

    def _get_iap_config_parameters(self):
        return super()._get_iap_config_parameters() + ['sms.endpoint']
