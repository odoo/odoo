# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class FrontdeskDrink(models.Model):
    _name = 'frontdesk.drink'
    _description = 'Frontdesk Drink'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True)
    drink_image = fields.Image()
    sequence = fields.Integer(default=1)
    notify_user_ids = fields.Many2many('res.users', string='People to Notify', required=True)
    active = fields.Boolean(default=True)
