# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrContractSalaryOffer(models.Model):
    _inherit = 'hr.contract.salary.offer'
    _description = 'Salary Package Offer'

    contract_type_id = fields.Many2one(
        'hr.contract.type', "Contract Type",
        compute='_compute_contract_type_id',
        store=True,
        readonly=False,
        tracking=True)
    new_car = fields.Boolean(
        string='Show "Company Car (To Order)"', tracking=True,
        compute="_compute_new_car",
        store=True,
        readonly=False,
        help="The employee will be able to choose a new car even if the maximum number of used cars available is reached.")
    show_new_car = fields.Boolean(tracking=True)
    car_id = fields.Many2one(
        'fleet.vehicle', string='Default Vehicle',
        compute='_compute_car_id',
        store=True,
        readonly=False, domain="[('vehicle_type', '=', 'car')]",
        help="Default employee's company car. If left empty, the default value will be the employee's current car.")
    additional_car_ids = fields.Many2many('fleet.vehicle', domain="[('vehicle_type', '=', 'car')]", string="Additional cars",
                                          help="You can add used cars to this field, they'll be added to the list for simulation purposes.")
    l10n_be_canteen_cost = fields.Float(
        compute='_compute_l10n_be_canteen_cost',
        store=True,
        string="Canteen Cost", readonly=False)
    country_code = fields.Char(related='contract_template_id.country_code', depends=['contract_template_id'])
    assigned_car_warning = fields.Char(compute='_compute_assigned_car_warning')
    wishlist_car_warning = fields.Char(compute='_compute_wishlist_car_warning')

    @api.depends('contract_template_id')
    def _compute_contract_type_id(self):
        for offer in self:
            offer.contract_type_id = offer.contract_template_id.contract_type_id

    @api.depends('applicant_id', 'contract_template_id.available_cars_amount', 'contract_template_id.max_unused_cars')
    def _compute_new_car(self):
        for offer in self:
            # new_car defaults to True for applicants
            if offer.applicant_id:
                offer.new_car = True
            else:
                offer.new_car = offer.contract_template_id.available_cars_amount < offer.contract_template_id.max_unused_cars

    @api.depends('applicant_id.partner_id', 'employee_id')
    def _compute_car_id(self):
        for offer in self:
            partner = self.env['res.partner']
            car = self.env['fleet.vehicle']
            if offer.employee_id:
                partner |= offer.employee_id.work_contact_id
                # In case the car was reserved for an applicant, while
                # the offer is sent for the corresponding employee
                if candidate_partner_id := offer.employee_id.sudo().candidate_id.partner_id:
                    partner |= candidate_partner_id
            elif offer.applicant_id:
                partner |= offer.applicant_id.partner_id
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
            offer.car_id = car

    @api.depends('contract_template_id')
    def _compute_l10n_be_canteen_cost(self):
        for offer in self:
            offer.l10n_be_canteen_cost = offer.contract_template_id.l10n_be_canteen_cost

    @api.depends('applicant_id.partner_id', 'employee_id', 'car_id')
    def _compute_assigned_car_warning(self):
        self.assigned_car_warning = False
        for offer in self:
            warning = []
            partners = self.env['res.partner']
            if offer.applicant_id:
                partners |= offer.applicant_id.partner_id
            elif offer.employee_id:
                partners |= offer.employee_id.work_contact_id
                if candidate_partner_id := offer.employee_id.sudo().candidate_id.partner_id:
                    partners |= candidate_partner_id
            if offer.car_id.driver_id and offer.car_id.driver_id not in partners:
                warning.append(f"Car is already assigned to {offer.car_id.driver_id.name} as a driver.")
            if offer.car_id.future_driver_id and offer.car_id.future_driver_id not in partners:
                warning.append(f"Car is already assigned to {offer.car_id.future_driver_id.name} as a future driver.")
            if warning:
                offer.assigned_car_warning = f"Warning: {' '.join(warning)}"

    @api.depends('new_car')
    def _compute_wishlist_car_warning(self):
        for offer in self:
            if offer.contract_template_id.available_cars_amount >= offer.contract_template_id.max_unused_cars:
                offer.wishlist_car_warning = _("We already have %s car(s) without driver(s) available",
                                              offer.employee_contract_id.available_cars_amount)
            else:
                offer.wishlist_car_warning = False
