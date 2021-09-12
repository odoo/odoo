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
from . lib import module_lib

import logging

_logger = logging.getLogger(__name__)

class SaasModule(models.Model):
    _inherit = 'saas.module'


    def set_default_path(self):
        for obj in self:
            IrDefault = obj.env['ir.default'].sudo()
            addons_path = IrDefault.get('res.config.settings', 'addons_path')
            obj.addons_path = addons_path

    is_published = fields.Boolean(string="Publised", default=False)
    price = fields.Integer(string="Price")
    auto_install = fields.Boolean(string="Auto Install Module", default=True)
    addons_path = fields.Char(string="Addons Path", compute="set_default_path", store=True, readonly=False)
    order_line_id = fields.Many2one(comodel_name="sale.order.line")
    contract_id = fields.Many2one(comodel_name="saas.contract")


    def toggle_module_publish(self):
        if not self.is_published:
            """
            Check whether the module exist in the path or not.
            """
            if self.auto_install:
                res = module_lib.check_if_module([self.addons_path], self.technical_name)
                if res.get('status'):
                    self.is_published = not self.is_published                  
                elif not res.get('msg'):
                    raise UserError("You have Selected Auto install for the Module but Module does not present on the Defautl path.")
                else:
                    raise UserError(res.get('msg'))
            else:
                self.is_published = not self.is_published
        else:
            self.is_published = not self.is_published


