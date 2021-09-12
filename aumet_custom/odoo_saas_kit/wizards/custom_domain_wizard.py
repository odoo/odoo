# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import api, models, fields
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class CustomDomainWizard(models.TransientModel):
    _name = "custom.domain.wizard"

    name = fields.Char(string="Domain Name")
    is_ssl_enable = fields.Boolean(string="Enable SSL/HTTPS")

    def save_domain(self):
        contract = self.env['saas.contract'].sudo().browse(self.env.context.get('instance_id'))
        contract.add_custom_domain(self.name, self.is_ssl_enable)