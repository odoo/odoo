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
        departure = fields.Datetime.to_datetime(self.departure_date)
        vehicles = self.env["resource.asset"].sudo().search([("is_vehicle", "=", True)])
        assignments = (
            self.env["resource.assignment"]
            .sudo()
            .search(
                [
                    ("assignee_id", "in", self.employee_ids.sudo().resource_id.ids),
                    ("custody_role", "=", "operator"),
                    ("resource_id", "in", vehicles.resource_id.ids),
                    "|",
                    ("date_end", "=", False),
                    ("date_end", ">", departure),
                ]
            )
        )
        assignments._end(departure)
