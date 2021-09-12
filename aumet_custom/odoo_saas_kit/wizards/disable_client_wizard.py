# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import api, fields, models
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class ClientDisable(models.TransientModel):
    _name = "saas.instance.inactive"

    name = fields.Char(string="Name")
    instance_id = fields.Integer(string="Instance Id")

    def inactive_client(self):
        record = self.env['saas.client'].browse([self.env.context.get('instance_id')])        
        record.inactive_client()

    def hold_contract(self):
        record = self.env['saas.contract'].browse([self.env.context.get('instance_id')])
        record.hold_contract()

    def drop_db(self):
        record = self.env['saas.client'].browse([self.env.context.get('instance_id')])        
        record.drop_db()

    def drop_container(self):
        record = self.env['saas.client'].browse([self.env.context.get('instance_id')])        
        record.drop_container()
