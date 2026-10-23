# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models

class ImportLogger(models.Model):
    _name = 'sh.import.log'
    _description = 'Helps you to maintain the activity done'
    _order = 'id desc'

    message = fields.Text("Message")
    datetime = fields.Datetime("Date & Time")
    sh_store_id = fields.Many2one('sh.import.store',string="Store")