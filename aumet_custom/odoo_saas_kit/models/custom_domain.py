# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import fields, api, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class CustomDomain(models.Model):
    _name = 'custom.domain'

    name = fields.Char(string="Domain Name")
    contract_id = fields.Many2one(comodel_name='saas.contract', string="Contract")
    setup_date = fields.Date(string="Setup Date")
    revoke_date = fields.Date(string="Revoke Date")

    def revoke_subdomain(self):
        response = self.contract_id.revoke_subdomain(self.name)
        self.revoke_date = fields.Date.today()