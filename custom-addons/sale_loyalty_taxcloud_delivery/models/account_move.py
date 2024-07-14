# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .taxcloud_request import TaxCloudRequest
from odoo import api, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_TaxCloudRequest(self, api_id, api_key):
        return TaxCloudRequest(api_id, api_key)
