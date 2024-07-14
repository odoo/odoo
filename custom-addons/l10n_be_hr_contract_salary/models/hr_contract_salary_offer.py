# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'
    _description = 'Salary Package Offer'

    contract_type_id = fields.Many2one(
        'hr.contract.type', "Contract Type", tracking=True)
    new_car = fields.Boolean(
        string="Force New Cars List", tracking=True,
        help="The employee will be able to choose a new car even if the maximum number of used cars available is reached.")
    show_new_car = fields.Boolean(tracking=True)
    car_id = fields.Many2one(
        'fleet.vehicle', string='Default Vehicle',
        readonly=False, domain="[('vehicle_type', '=', 'car')]",
        help="Default employee's company car. If left empty, the default value will be the employee's current car.")
    l10n_be_canteen_cost = fields.Float(
        string="Canteen Cost", readonly=False)
