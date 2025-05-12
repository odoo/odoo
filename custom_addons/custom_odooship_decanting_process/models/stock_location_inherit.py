# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.location'


    site_code_id = fields.Many2one('site.code.configuration', string='Site Code')
    filled = fields.Boolean(string="Is Filled", default=False, help="Indicates if the location is occupied")
    automation_manual = fields.Char(string='Automation/Manual Location Type')
