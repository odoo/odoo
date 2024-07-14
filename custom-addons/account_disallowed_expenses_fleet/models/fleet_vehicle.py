# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    rate_ids = fields.One2many('fleet.disallowed.expenses.rate', 'vehicle_id', string='Disallowed Expenses Rate')


class FleetDisallowedExpensesRate(models.Model):
    _name = 'fleet.disallowed.expenses.rate'
    _description = 'Vehicle Disallowed Expenses Rate'
    _order = 'date_from desc'

    rate = fields.Float(string='%', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    company_id = fields.Many2one('res.company', string='Company', related='vehicle_id.company_id', readonly=True)
