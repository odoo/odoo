# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ServerAction(models.Model):
    _inherit = "ir.actions.server"

    usage = fields.Selection(selection_add=[
        ('base_automation', 'Automation Rule')
    ], ondelete={'base_automation': 'cascade'})
    base_automation_id = fields.Many2one('base.automation', string='Automation Rule', ondelete='cascade')
