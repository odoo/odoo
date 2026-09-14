from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    mobility_card = fields.Char(
        compute="_compute_mobility_card",
        store=True,
    )
    driver_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Driver (Employee)",
        compute="_compute_driver_employee_id",
        store=True,
        index="btree_not_null",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    driver_employee_name = fields.Char(related="driver_employee_id.name")
    future_driver_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Future Driver (Employee)",
        compute="_compute_future_driver_employee_id",
        store=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )

    @api.depends("driver_id")
    def _compute_driver_employee_id(self):
        employees_by_partner_id_and_company_id = self.env["hr.employee"]._read_group(
            domain=[("partner_id", "in", self.driver_id.ids)],
            groupby=["partner_id", "company_id"],
            aggregates=["id:recordset"],
        )
        employees_by_partner_id_and_company_id = {
            (partner, company): employee
            for partner, company, employee in employees_by_partner_id_and_company_id
        }
        for vehicle in self:
            employees = employees_by_partner_id_and_company_id.get(
                (vehicle.driver_id, vehicle.company_id)
            )
            vehicle.driver_employee_id = employees[0] if employees else False

    @api.depends("future_driver_id")
    def _compute_future_driver_employee_id(self):
        employees_by_partner_id_and_company_id = self.env["hr.employee"]._read_group(
            domain=[("partner_id", "in", self.future_driver_id.ids)],
            groupby=["partner_id", "company_id"],
            aggregates=["id:recordset"],
        )
        employees_by_partner_id_and_company_id = {
            (partner, company): employee
            for partner, company, employee in employees_by_partner_id_and_company_id
        }
        for vehicle in self:
            employees = employees_by_partner_id_and_company_id.get(
                (vehicle.future_driver_id, vehicle.company_id)
            )
            vehicle.future_driver_employee_id = employees[0] if employees else False

    @api.depends("driver_id")
    def _compute_mobility_card(self):
        for vehicle in self:
            employee = self.env["hr.employee"]
            if vehicle.driver_id:
                employee = employee.search(
                    [("partner_id", "=", vehicle.driver_id.id)], limit=1
                )
                if not employee:
                    employee = employee.search(
                        [("user_id.partner_id", "=", vehicle.driver_id.id)], limit=1
                    )
            _debug.logic(
                "mobility_card_from_employee", vehicle=vehicle, employee=employee
            )
            vehicle.mobility_card = employee.mobility_card

    def _update_create_write_vals(self, vals):
        if "driver_employee_id" in vals:
            partner = False
            if vals["driver_employee_id"]:
                employee = (
                    self.env["hr.employee"].sudo().browse(vals["driver_employee_id"])
                )
                partner = employee.partner_id.id
            vals["driver_id"] = partner
        elif "driver_id" in vals:
            employee = False
            if vals["driver_id"]:
                employee_ids = (
                    self.env["hr.employee"]
                    .sudo()
                    .search([("partner_id", "=", vals["driver_id"])], limit=2)
                )
                if len(employee_ids) == 1:
                    employee = employee_ids[0].id
                _debug.logic(
                    "driver_employee_from_partner",
                    partner=vals["driver_id"],
                    matches=len(employee_ids),
                    resolved=employee,
                )
            vals["driver_employee_id"] = employee

        if "future_driver_employee_id" in vals:
            partner = False
            if vals["future_driver_employee_id"]:
                employee = (
                    self.env["hr.employee"]
                    .sudo()
                    .browse(vals["future_driver_employee_id"])
                )
                partner = employee.partner_id.id
            vals["future_driver_id"] = partner
        elif "future_driver_id" in vals:
            employee = False
            if vals["future_driver_id"]:
                employee_ids = (
                    self.env["hr.employee"]
                    .sudo()
                    .search([("partner_id", "=", vals["future_driver_id"])], limit=2)
                )
                if len(employee_ids) == 1:
                    employee = employee_ids[0].id
                _debug.logic(
                    "future_driver_employee_from_partner",
                    partner=vals["future_driver_id"],
                    matches=len(employee_ids),
                    resolved=employee,
                )
            vals["future_driver_employee_id"] = employee

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._update_create_write_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._update_create_write_vals(vals)
        if "driver_employee_id" in vals:
            for vehicle in self:
                if (
                    vehicle.driver_employee_id
                    and vehicle.driver_employee_id.id != vals["driver_employee_id"]
                ):
                    partners_to_unsubscribe = vehicle.driver_id.ids
                    employee = vehicle.driver_employee_id
                    if employee and employee.user_id.partner_id:
                        partners_to_unsubscribe.append(employee.user_id.partner_id.id)
                    _debug.lifecycle(
                        "driver_changed_unsubscribe",
                        vehicle=vehicle,
                        partners=len(partners_to_unsubscribe),
                    )
                    vehicle.message_unsubscribe(partner_ids=partners_to_unsubscribe)
        return super().write(vals)

    def action_view_employee(self):
        self.check_singleton()
        return {
            "name": _("Related Employee"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "form",
            "res_id": self.driver_employee_id.id,
        }

    def open_assignation_logs(self):
        action = super().open_assignation_logs()
        action["views"] = [
            [
                self.env.ref("hr_fleet.fleet_vehicle_assignation_log_view_list").id,
                "list",
            ]
        ]
        return action
