# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LunchLocation(models.Model):
    _name = 'lunch.location'
    _description = 'Lunch Locations'

    name = fields.Char('Location Name')
    address = fields.Text('Address')
