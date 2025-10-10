# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_cars_count = fields.Integer(compute="_compute_employee_cars_count", string="Cars", groups="fleet.fleet_group_manager")
    car_ids = fields.One2many(
        'fleet.vehicle', 'driver_employee_id', string='Vehicles (private)',
        groups="fleet.fleet_group_manager,hr.group_hr_user",
    )
    license_plate = fields.Char(compute="_compute_license_plate", search="_search_license_plate", groups="hr.group_hr_user")
    mobility_card = fields.Char(groups="fleet.fleet_group_user")

    def action_open_employee_cars(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.assignation.log",
            "views": [[self.env.ref("hr_fleet.fleet_vehicle_assignation_log_employee_view_list").id, "list"], [False, "form"]],
            "domain": [("driver_employee_id", "in", self.ids), ("driver_id", "in", self.work_contact_id.ids)],
            "context": dict(self.env.context, default_driver_id=self.user_id.partner_id.id, default_driver_employee_id=self.id),
            "name": self.env._("Cars History"),
        }

    @api.depends('private_car_plate', 'car_ids.license_plate')
    def _compute_license_plate(self):
        for employee in self:
            if employee.private_car_plate and employee.car_ids.license_plate:
                employee.license_plate = ' '.join(employee.car_ids.filtered('license_plate').mapped('license_plate') + [employee.private_car_plate])
            else:
                employee.license_plate = ' '.join(employee.car_ids.filtered('license_plate').mapped('license_plate')) or employee.private_car_plate

    def _search_license_plate(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return ['|', ('car_ids.license_plate', operator, value), ('private_car_plate', operator, value)]

    def _compute_employee_cars_count(self):
        rg = self.env['fleet.vehicle.assignation.log']._read_group([
            ('driver_employee_id', 'in', self.ids), ('driver_id', 'in', self.work_contact_id.ids),
        ], ['driver_employee_id'], ['__count'])
        cars_count = {driver_employee.id: count for driver_employee, count in rg}
        for employee in self:
            employee.employee_cars_count = cars_count.get(employee.id, 0)

    @api.constrains('work_contact_id')
    def _check_work_contact_id(self):
        no_address = self.filtered(lambda r: not r.work_contact_id)
        car_ids = self.env['fleet.vehicle'].sudo().search([
            ('driver_employee_id', 'in', no_address.ids),
        ])
        # Prevent from removing employee address when linked to a car
        if car_ids:
            raise ValidationError(_('Cannot remove address from employees with linked cars.'))

    def write(self, vals):
        # Update car partner when it is changed on the employee
        old_work_contact_id_mapping = {e.id: e.work_contact_id.id for e in self}
        res = super().write(vals)

        # Update car partner when it is changed on the employee needs to be done after because of _sync_user
        if 'work_contact_id' in vals:
            for employee in self:
                if vals['work_contact_id'] != old_work_contact_id_mapping[employee.id]:
                    car_ids = self.env['fleet.vehicle'].sudo().search([
                        '|',
                            ('driver_employee_id', '=', employee.id),
                            ('future_driver_employee_id', '=', employee.id),
                    ])
                    if car_ids:
                        car_ids.filtered(lambda c: c.driver_employee_id.id == employee.id).write({
                            'driver_id': vals['work_contact_id'],
                        })
                        car_ids.filtered(lambda c: c.future_driver_employee_id.id == employee.id).write({
                            'future_driver_id': vals['work_contact_id'],
                        })

        if 'mobility_card' in vals:
            car_ids = self.env['fleet.vehicle'].sudo().search([
                ('driver_employee_id', 'in', self.ids),
            ])
            car_ids._compute_mobility_card()
        return res


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    mobility_card = fields.Char(readonly=True)
