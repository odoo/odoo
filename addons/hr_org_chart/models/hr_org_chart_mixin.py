from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    child_all_count = fields.Integer(
        string="Indirect Subordinates Count",
        compute="_compute_subordinates",
        compute_sudo=True,
        recursive=True,
        store=False,
    )
    department_color = fields.Integer(
        related="department_id.color",
        string="Department Color",
    )
    child_count = fields.Integer(
        string="Direct Subordinates Count",
        compute="_compute_child_count",
        compute_sudo=True,
        recursive=True,
    )

    def _get_subordinates(self, parents=None):
        if not parents:
            parents = self.env[self._name]

        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_ids - parents
        child_subordinates = (
            direct_subordinates._get_subordinates(parents=parents)
            if direct_subordinates
            else self.browse()
        )
        indirect_subordinates |= child_subordinates
        return indirect_subordinates | direct_subordinates

    @api.depends("child_ids", "child_ids.child_all_count")
    def _compute_subordinates(self):
        _debug.perf.count("subordinates_walked", employees=self)
        for employee in self:
            employee.subordinate_ids = employee._get_subordinates()
            employee.child_all_count = len(employee.subordinate_ids)

    @api.depends_context("uid", "company")
    @api.depends("parent_id")
    def _compute_is_subordinate(self):
        subordinates = self.env.user.employee_id.subordinate_ids
        _debug.logic("is_subordinate", user=self.env.user, subordinates=subordinates)
        if not subordinates:
            self.is_subordinate = False
        else:
            for employee in self:
                employee.is_subordinate = employee in subordinates

    def _search_is_subordinate(self, operator, value):
        if operator != "in":
            return NotImplemented
        subordinates = self.env.user.employee_id.subordinate_ids
        return [("id", "in", subordinates.ids)]

    def _compute_child_count(self):
        employee_read_group = self._read_group(
            [("parent_id", "in", self.ids)],
            ["parent_id"],
            ["id:count"],
        )
        child_count_per_parent_id = dict(employee_read_group)
        for employee in self:
            employee.child_count = child_count_per_parent_id.get(employee._origin, 0)
