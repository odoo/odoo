# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class GenerateSimulationLink(models.TransientModel):
    _inherit = 'generate.simulation.link'

    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type",
                                       default=lambda self: self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi',
                                                                         raise_if_not_found=False))

    new_car = fields.Boolean(string="Force New Cars List", help="The employee will be able to choose a new car even if the maximum number of used cars available is reached.")
    show_new_car = fields.Boolean(compute='_compute_show_new_car', store=True)
    car_id = fields.Many2one('fleet.vehicle', string='Default Vehicle', compute='_compute_car_id', store=True, readonly=False, domain="[('vehicle_type', '=', 'car')]", help="Default employee's company car. If left empty, the default value will be the employee's current car.")
    l10n_be_canteen_cost = fields.Float(
        string="Canteen Cost", compute='_compute_l10n_be_canteen_cost', store=True, readonly=False)
    assigned_car_warning = fields.Char(compute='_compute_assigned_car_warning')

    @api.depends('applicant_id.partner_id', 'employee_id.partner_id', 'car_id')
    def _compute_assigned_car_warning(self):
        model = self.env.context.get('active_model')
        self.assigned_car_warning = False
        for link in self:
            warning = []
            partners = self.env['res.partner']
            if model == 'hr.contract' and link.employee_id:
                partners |= link.employee_id.work_contact_id
                if link.employee_id.applicant_id:
                    partners |= link.employee_id.applicant_id.partner_id
            elif model == 'hr.applicant':
                partners |= link.applicant_id.partner_id if link.applicant_id else False
            if link.car_id.driver_id and link.car_id.driver_id not in partners:
                warning.append(f"Car is already assigned to {link.car_id.driver_id.name} as a driver.")
            if link.car_id.future_driver_id and link.car_id.future_driver_id not in partners:
                warning.append(f"Car is already assigned to {link.car_id.future_driver_id.name} as a future driver.")
            if warning:
                link.assigned_car_warning = f"Warning: {' '.join(warning)}"

    @api.depends('applicant_id.partner_id', 'employee_id.partner_id')
    def _compute_car_id(self):
        model = self.env.context.get('active_model')
        for wizard in self:
            partner = self.env['res.partner']
            car = self.env['fleet.vehicle']
            if model == 'hr.contract':
                if wizard.employee_id:
                    partner |= wizard.employee_id.work_contact_id
                    # In case the car was reserved for an applicant, while
                    # the simulation link is sent for the corresponding employee
                    if wizard.employee_id.applicant_id:
                        partner |= wizard.employee_id.applicant_id.partner_id
            elif model == 'hr.applicant':
                partner |= wizard.applicant_id.partner_id if wizard.applicant_id else False
            if partner:
                car_is_driver = self.env['fleet.vehicle'].search([
                    ('future_driver_id', '=', False),
                    ('driver_id', 'in', partner.ids),
                    ('vehicle_type', '=', 'car'),
                ], limit=1)
                car_is_future_driver = self.env['fleet.vehicle'].search([
                    ('future_driver_id', 'in', partner.ids),
                    ('driver_id', '=', False),
                    ('vehicle_type', '=', 'car'),
                ], limit=1)
                car = car_is_driver or car_is_future_driver
            wizard.car_id = car if car else False

    @api.depends('contract_id.available_cars_amount', 'contract_id.max_unused_cars')
    def _compute_show_new_car(self):
        for wizard in self:
            if wizard.env.context.get('active_model') == "hr.applicant":
                wizard.show_new_car = False
                wizard.new_car = True
            else:
                wizard.show_new_car = wizard.contract_id.available_cars_amount >= wizard.contract_id.max_unused_cars

    @api.depends('contract_id.l10n_be_canteen_cost')
    def _compute_l10n_be_canteen_cost(self):
        for wizard in self:
            wizard.l10n_be_canteen_cost = wizard.contract_id.l10n_be_canteen_cost

    def _get_offer_values(self):
        values = super()._get_offer_values()
        values.update({
            'contract_type_id': self.contract_type_id.id,
            'new_car': self.new_car,
            'show_new_car': self.show_new_car,
            'car_id': self.car_id.id,
            'l10n_be_canteen_cost': self.l10n_be_canteen_cost,
        })
        return values
