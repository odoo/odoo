from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = "hr.departure.wizard"

    release_campany_car = fields.Boolean(
        string="Release Company Car",
        default=lambda self: self.env.user.has_group("fleet.fleet_group_user"),
    )

    def action_register_departure(self):
        action = super().action_register_departure()
        if self.release_campany_car:
            self._free_company_car()
        return action

    def _free_company_car(self):
        drivers = (
            self.employee_ids.user_id.partner_id | self.employee_ids.sudo().partner_id
        )
        assignations = self.env["fleet.vehicle.assignation.log"].search(
            [
                ("driver_id", "in", drivers.ids),
                "|",
                ("date_end", "=", False),
                ("date_end", ">", self.departure_date),
            ]
        )
        assignations.write({"date_end": self.departure_date})
        cars = self.env["fleet.vehicle"].search([("driver_id", "in", drivers.ids)])
        cars.write({"driver_id": False, "driver_employee_id": False})
