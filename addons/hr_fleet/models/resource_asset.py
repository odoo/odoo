from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    driver_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Driver (Employee)",
        compute="_compute_driver_employees",
        inverse="_inverse_driver_employee_id",
        search="_search_driver_employee_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    future_driver_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Future Driver (Employee)",
        compute="_compute_driver_employees",
        inverse="_inverse_future_driver_employee_id",
        search="_search_future_driver_employee_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    mobility_card = fields.Char(related="driver_employee_id.mobility_card")

    @api.depends("driver_id", "future_driver_id")
    def _compute_driver_employees(self):
        employees = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [("resource_id", "in", (self.driver_id | self.future_driver_id).ids)]
            )
        )
        by_resource = {employee.resource_id: employee for employee in employees}
        for asset in self:
            asset.driver_employee_id = by_resource.get(asset.driver_id, False)
            asset.future_driver_employee_id = by_resource.get(
                asset.future_driver_id, False
            )

    def _inverse_driver_employee_id(self):
        for asset in self:
            asset.driver_id = asset.driver_employee_id.sudo().resource_id

    def _inverse_future_driver_employee_id(self):
        for asset in self:
            asset.future_driver_id = asset.future_driver_employee_id.sudo().resource_id

    def _search_driver_employee_id(self, operator, value):
        return self._search_employee_driver("driver_id", operator, value)

    def _search_future_driver_employee_id(self, operator, value):
        return self._search_employee_driver("future_driver_id", operator, value)

    def _search_employee_driver(self, field_name, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        ids = [value] if isinstance(value, (int, bool)) else list(value)
        resources = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .browse([i for i in ids if i])
            .resource_id
        )
        wanted = resources.ids + ([False] if not all(ids) else [])
        return [(field_name, operator, wanted)]

    def action_view_employee(self):
        self.check_singleton()
        return {
            "name": self.env._("Related Employee"),
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "view_mode": "form",
            "res_id": self.driver_employee_id.id,
        }
