# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('sales_team_dashboard', 'Sales Team Dashboard')])
