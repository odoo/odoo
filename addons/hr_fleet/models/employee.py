from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    employee_cars_count = fields.Integer(
        string="Cars",
        compute="_compute_employee_cars_count",
        groups="fleet.fleet_group_manager",
    )
    car_ids = fields.One2many(
        comodel_name="fleet.vehicle",
        inverse_name="driver_employee_id",
        string="Vehicles (private)",
        groups="fleet.fleet_group_manager,hr.group_hr_user",
    )
    license_plate = fields.Char(
        compute="_compute_license_plate",
        search="_search_license_plate",
        groups="hr.group_hr_user",
    )
    mobility_card = fields.Char(groups="fleet.fleet_group_user")

    def action_view_employee_cars(self):
        self.check_singleton()

        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.assignation.log",
            "views": [
                [
                    self.env.ref(
                        "hr_fleet.fleet_vehicle_assignation_log_employee_view_list"
                    ).id,
                    "list",
                ],
                [False, "form"],
            ],
            "domain": [
                ("driver_employee_id", "in", self.ids),
                ("driver_id", "in", self.partner_id.ids),
            ],
            "context": dict(
                self.env.context,
                default_driver_id=self.user_id.partner_id.id,
                default_driver_employee_id=self.id,
            ),
            "name": self.env._("Cars History"),
        }

    @api.depends("private_car_plate", "car_ids.license_plate")
    def _compute_license_plate(self):
        for employee in self:
            if employee.private_car_plate and employee.car_ids.license_plate:
                employee.license_plate = " ".join(
                    employee.car_ids.filtered("license_plate").mapped("license_plate")
                    + [employee.private_car_plate]
                )
            else:
                employee.license_plate = (
                    " ".join(
                        employee.car_ids.filtered("license_plate").mapped(
                            "license_plate"
                        )
                    )
                    or employee.private_car_plate
                )

    def _search_license_plate(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [
            "|",
            ("car_ids.license_plate", operator, value),
            ("private_car_plate", operator, value),
        ]

    def _compute_employee_cars_count(self):
        rg = self.env["fleet.vehicle.assignation.log"]._read_group(
            [
                ("driver_employee_id", "in", self.ids),
                ("driver_id", "in", self.partner_id.ids),
            ],
            ["driver_employee_id"],
            ["__count"],
        )
        cars_count = {driver_employee.id: count for driver_employee, count in rg}
        _debug.perf.count("employee_cars_counted", employees=self, rows=len(cars_count))
        for employee in self:
            employee.employee_cars_count = cars_count.get(employee.id, 0)

    @api.constrains("partner_id")
    def _check_work_contact_id(self):
        no_address = self.filtered(lambda r: not r.partner_id)
        car_ids = (
            self.env["fleet.vehicle"]
            .sudo()
            .search(
                [
                    ("driver_employee_id", "in", no_address.ids),
                ]
            )
        )
        if car_ids:
            _debug.logic(
                "work_contact_removal_refused",
                employees=no_address,
                vehicles=car_ids,
            )
            raise ValidationError(
                _("Cannot remove address from employees with linked cars.")
            )

    def write(self, vals):
        old_work_contact_id_mapping = {e.id: e.partner_id.id for e in self}
        res = super().write(vals)

        _debug.lifecycle("employee_write", employees=self, fields=list(vals))
        if "partner_id" in vals or "user_id" in vals:
            for employee in self:
                new_contact_id = employee.partner_id.id
                if new_contact_id != old_work_contact_id_mapping[employee.id]:
                    car_ids = (
                        self.env["fleet.vehicle"]  # noqa: E8507 - one lookup per employee whose work contact changed
                        .sudo()
                        .search(
                            [
                                "|",
                                ("driver_employee_id", "=", employee.id),
                                ("future_driver_employee_id", "=", employee.id),
                            ]
                        )
                    )
                    if car_ids:
                        _debug.pipeline(
                            "driver_contact_followed",
                            employee=employee,
                            vehicles=car_ids,
                            contact=new_contact_id,
                        )
                        car_ids.filtered(
                            lambda c, employee=employee: (
                                c.driver_employee_id.id == employee.id
                            )
                        ).write({"driver_id": new_contact_id})
                        car_ids.filtered(
                            lambda c, employee=employee: (
                                c.future_driver_employee_id.id == employee.id
                            )
                        ).write({"future_driver_id": new_contact_id})

        if "mobility_card" in vals:
            car_ids = (
                self.env["fleet.vehicle"]
                .sudo()
                .search(
                    [
                        ("driver_employee_id", "in", self.ids),
                    ]
                )
            )
            _debug.pipeline(
                "mobility_card_propagated", employees=self, vehicles=car_ids
            )
            car_ids._compute_mobility_card()
        return res
