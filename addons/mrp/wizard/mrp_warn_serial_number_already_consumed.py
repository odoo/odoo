# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpWarnSerialNumberAlreadyConsumed(models.TransientModel):
    _name = 'mrp.warn.serial.number.already.consumed'
    _description = 'Warning Serial Number Already Consumed'

    mrp_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        self.mrp_id.mark_done()
