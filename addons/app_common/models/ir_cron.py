# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models, modules, tools, _

_logger = logging.getLogger(__name__)

class IrCron(models.Model):
    _inherit = "ir.cron"

    trigger_user_id = fields.Many2one('res.users', string='Last Trigger User')

    def method_direct_trigger(self):
        self.write({'trigger_user_id': self.env.user.id})
        return super(IrCron, self).method_direct_trigger()
