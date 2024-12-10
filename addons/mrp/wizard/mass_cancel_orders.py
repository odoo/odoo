# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpMassCancel(models.TransientModel):
    _name = 'mrp.mass.cancel.orders'
    _description = "Cancel multiple Manufacturing Orders"

    mrp_production_count = fields.Integer(default=lambda self: len(self.env.context.get('active_ids')))

    def mass_cancel(self):
        mrp_production_ids = self.env['mrp.production'].browse(self.env.context.get('active_ids'))
        mrp_production_ids.action_cancel()
