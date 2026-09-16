from odoo import api, fields, models
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_cars_count = fields.Integer(
        string="Cars",
        compute="_compute_employee_cars_count",
        groups="fleet.fleet_group_manager",
    )
    car_ids = fields.Many2many(
        comodel_name="resource.asset",
        string="Vehicles (private)",
        compute="_compute_car_ids",
        search="_search_car_ids",
        groups="fleet.fleet_group_manager,hr.group_hr_user",
    )
    license_plate = fields.Char(
        compute="_compute_license_plate",
        search="_search_license_plate",
        groups="hr.group_hr_user",
    )
    mobility_card = fields.Char(groups="fleet.fleet_group_user")

    def _compute_car_ids(self):
        vehicles = (
            self.env["resource.asset"]
            .sudo()
            .search(
                [("is_vehicle", "=", True), ("operator_id", "in", self.resource_id.ids)]
            )
        )
        for employee in self:
            employee.car_ids = vehicles.filtered(
                lambda vehicle, employee=employee: (
                    vehicle.operator_id == employee.resource_id
                )
            )

    def _search_car_ids(self, operator, value):
        if operator not in ("in", "not in", "any", "not any"):
            return NotImplemented
        if operator in ("any", "not any"):
            vehicles = self.env["resource.asset"].sudo().search(value)
        else:
            vehicles = self.env["resource.asset"].sudo().browse(value)
        domain = Domain("resource_id", "in", vehicles.operator_id.ids)
        return ~domain if operator.startswith("not") else domain

    @api.depends("private_car_plate")
    def _compute_license_plate(self):
        for employee in self:
            plates = (
                employee.sudo()
                .car_ids.filtered("license_plate")
                .mapped("license_plate")
            )
            if employee.private_car_plate:
                plates.append(employee.private_car_plate)
            employee.license_plate = " ".join(plates) or False

    def _search_license_plate(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        vehicles = (
            self.env["resource.asset"]
            .sudo()
            .search([("is_vehicle", "=", True), ("license_plate", operator, value)])
        )
        return Domain("resource_id", "in", vehicles.operator_id.ids) | Domain(
            "private_car_plate", operator, value
        )

    def _compute_employee_cars_count(self):
        counts = dict(
            self.env["resource.assignment"]
            .sudo()
            .with_context(active_test=False)
            ._read_group(
                [
                    ("assignee_id", "in", self.resource_id.ids),
                    ("custody_role", "=", "operator"),
                ],
                ["assignee_id"],
                ["__count"],
            )
        )
        for employee in self:
            employee.employee_cars_count = counts.get(employee.resource_id, 0)

    def action_view_employee_cars(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "resource.assignment",
            "view_mode": "list,form",
            "domain": [
                ("assignee_id", "=", self.resource_id.id),
                ("custody_role", "=", "operator"),
            ],
            "context": {
                "default_assignee_id": self.resource_id.id,
                "default_role": "operator",
                "active_test": False,
            },
            "name": self.env._("Cars History"),
        }
