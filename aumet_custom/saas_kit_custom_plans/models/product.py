# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import models, fields, api
from odoo.exceptions import UserError, Warning

import logging

_logger = logging.getLogger(__name__)

class SaasModuleProduct(models.Model):
    _inherit = 'product.product'

    is_saas_module = fields.Boolean(string="For Saas Module", default=False)

    @api.onchange('is_saas_module')
    def change_saas_module(self):
        if self.is_saas_module:
            self.saas_plan_id = None
            self.is_user_pricing = False
