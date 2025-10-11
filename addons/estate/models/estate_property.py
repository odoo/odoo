# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from datetime import date, datetime, time
from odoo.tools import date_utils

class EstateModel(models.Model):
    _name = "estate_property"
    _description = "Estate Property"

    today = fields.Datetime.now()

    name = fields.Char("Title",required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, default=date_utils.add(today, months=3))
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True,copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
      string='Type',
      selection=[('north', 'North'), ('south','South'), ('east', 'East'), ('west','West')]
    )
    active = fields.Boolean('Active', default=False)
    status = fields.Selection(
        string='Status',
        selection=[
          ('new', 'New'), 
          ('offer received', 'Offer Received'), 
          ('offer accepted', 'Offered Accepted'),
          ('sold', 'Sold'),
          ('cancelled', 'Cancelled')
        ],
        default='new'
      )