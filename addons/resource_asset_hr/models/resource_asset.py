from collections import defaultdict

from odoo import api, fields, models

EMPLOYEE_CUSTODY_FIELDS = {
    "operator_employee_id": "operator_id",
    "future_operator_employee_id": "future_operator_id",
    "manager_employee_id": "manager_id",
}


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    operator_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Operator (Employee)",
        compute="_compute_custody_employees",
        inverse="_inverse_operator_employee_id",
        search="_search_operator_employee_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    future_operator_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Future Operator (Employee)",
        compute="_compute_custody_employees",
        inverse="_inverse_future_operator_employee_id",
        search="_search_future_operator_employee_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    manager_employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Manager (Employee)",
        compute="_compute_custody_employees",
        inverse="_inverse_manager_employee_id",
        search="_search_manager_employee_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )

    @api.depends("operator_id", "future_operator_id", "manager_id")
    def _compute_custody_employees(self):
        resources = self.operator_id | self.future_operator_id | self.manager_id
        employees = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("resource_id", "in", resources.ids)])
        )
        by_resource = {employee.resource_id: employee for employee in employees}
        for asset in self:
            for employee_field, resource_field in EMPLOYEE_CUSTODY_FIELDS.items():
                asset[employee_field] = by_resource.get(asset[resource_field], False)

    def _inverse_custody_employee(self, employee_field):
        # Through write, so the resource field's own inverse runs: an assignment
        # written inside another inverse would otherwise never reach the table.
        # Grouped by holder, so a batch writing one holder is one write.
        resource_field = EMPLOYEE_CUSTODY_FIELDS[employee_field]
        by_resource = defaultdict(self.browse)
        for asset in self:
            by_resource[asset[employee_field].sudo().resource_id] |= asset
        for resource, assets in by_resource.items():
            assets.write({resource_field: resource.id})

    def _inverse_operator_employee_id(self):
        self._inverse_custody_employee("operator_employee_id")

    def _inverse_future_operator_employee_id(self):
        self._inverse_custody_employee("future_operator_employee_id")

    def _inverse_manager_employee_id(self):
        self._inverse_custody_employee("manager_employee_id")

    def _search_custody_employee(self, employee_field, operator, value):
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
        return [(EMPLOYEE_CUSTODY_FIELDS[employee_field], operator, wanted)]

    def _search_operator_employee_id(self, operator, value):
        return self._search_custody_employee("operator_employee_id", operator, value)

    def _search_future_operator_employee_id(self, operator, value):
        return self._search_custody_employee(
            "future_operator_employee_id", operator, value
        )

    def _search_manager_employee_id(self, operator, value):
        return self._search_custody_employee("manager_employee_id", operator, value)

    @api.model
    def _employee_by_resource(self, resources):
        employees = (
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=False)
            .search([("resource_id", "in", resources.ids)])
        )
        return {employee.resource_id.id: employee for employee in employees}


def live_custody_subquery(role, asset_alias, alias):
    """A lateral subquery naming the employee who holds `role` on the asset right
    now: the latest started live assignment, so an asset joins at most one row
    and a report's groups do not split. Use it as ``LEFT JOIN LATERAL {subquery}
    ON TRUE``."""
    return f"""(
                SELECT e.id AS employee_id
                  FROM resource_assignment ra
                  JOIN hr_employee e ON e.resource_id = ra.assignee_id
                 WHERE ra.resource_id = {asset_alias}.resource_id
                   AND ra.custody_role = '{role}'
                   AND ra.active
                   AND ra.date_start <= (clock_timestamp() AT TIME ZONE 'UTC')
                   AND (ra.date_end IS NULL OR ra.date_end > (clock_timestamp() AT TIME ZONE 'UTC'))
                 ORDER BY ra.date_start DESC, ra.id DESC
                 LIMIT 1
            ) {alias}"""
