# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.modules.loading import force_demo
from odoo.addons.base.models.ir_module import assert_log_admin_access


class IrDemo(models.TransientModel):

    _name = 'ir.demo'
    _description = 'Demo'

    @assert_log_admin_access
    def install_demo(self):
        force_demo(self.env)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/odoo',
        }
