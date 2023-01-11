# -*- coding: utf-8 -*-

from odoo import api, fields, models

class res_company(models.Model):
    _inherit = "res.company"

    is_reset_open_reading = fields.Boolean(string='Is Reset Open Reading', default=False)
    reset_open_reading_amount = fields.Float(string='Reset Open Reading Amount')
    reset_counter = fields.Integer(string='Reset Counter')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_reset_open_reading = fields.Boolean(related='company_id.is_reset_open_reading', string="Is Reset Open Reading", readonly=False)
    reset_open_reading_amount = fields.Float(related='company_id.reset_open_reading_amount', string='Reset Open Reading Amount', readonly=False)
    reset_counter = fields.Integer(related='company_id.reset_counter', string='Reset Counter', readonly=True)
