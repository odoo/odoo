# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.today()
        vehicles = super().create(vals_list)
        new_rates = []
        for vehicle in vehicles:
            if vehicle._from_be():
                new_rates.append({
                    'vehicle_id': vehicle.id,
                    'rate': 100 - vehicle.tax_deduction*100,
                    'date_from': today
                })
        if new_rates:
            self.env["fleet.disallowed.expenses.rate"].sudo().create(new_rates)
        return vehicles

    def write(self, vals):
        result = super(FleetVehicle, self).write(vals)
        today = fields.Date.today()
        # Check if we modified fields that could impact the actual tax_deduction
        if any(key in vals for key in ['fuel_type', 'co2', 'horsepower']):
            new_rates = []
            for vehicle in self:
                if vehicle._from_be():
                    rate = vehicle.rate_ids.filtered(lambda r: (r.date_from == today))
                    new_rate = {
                        'vehicle_id': vehicle.id,
                        'rate': 100 - vehicle.tax_deduction*100,
                        'date_from': today
                    }
                    if rate:
                        rate.sudo().update(new_rate)
                    else:
                        new_rates.append(new_rate)
            if new_rates:
                self.env["fleet.disallowed.expenses.rate"].sudo().create(new_rates)
        return result

    def action_view_disallowed_expenses_rate(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("l10n_be_account_disallowed_expenses_fleet.action_view_disallowed_expenses_rate")
        action.update({
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'dialog_size': 'medium'},
            'target': 'new'
        })
        return action



class FleetDisallowedExpensesRate(models.Model):
    _name = 'fleet.disallowed.expenses.rate'
    _description = 'Vehicle Disallowed Expenses Rate'
    _order = 'date_from desc'
    _inherit = 'fleet.disallowed.expenses.rate'

    tax_deduction = fields.Float(string='Tax Deduction %', compute='_compute_tax_deduction')

    @api.depends('rate')
    def _compute_tax_deduction(self):
        for rate in self:
            rate.tax_deduction = 100 - rate.rate
