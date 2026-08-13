# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    child_all_count = fields.Integer(
        'Indirect Subordinates Count',
        compute='_compute_subordinates', recursive=True, store=False,
        compute_sudo=True)
    department_color = fields.Integer("Department Color", related="department_id.color")
    child_count = fields.Integer(
        'Direct Subordinates Count',
        compute='_compute_child_count', recursive=True,
        compute_sudo=True,
    )

    def _get_subordinates(self, parents=None):
        """
        Helper function to compute subordinates_ids.
        Get all subordinates (direct and indirect) of an employee.
        An employee can be a manager of his own manager (recursive hierarchy; e.g. the CEO is manager of everyone but is also
        member of the RD department, managed by the CTO itself managed by the CEO).
        In that case, the manager in not counted as a subordinate if it's in the 'parents' set.
        """
        if not parents:
            parents = self.env[self._name]

        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_ids - parents
        child_subordinates = direct_subordinates._get_subordinates(parents=parents) if direct_subordinates else self.browse()
        indirect_subordinates |= child_subordinates
        return indirect_subordinates | direct_subordinates

    @api.depends('child_ids', 'child_ids.child_all_count')
    def _compute_subordinates(self):
        for employee in self:
            employee.subordinate_ids = employee._get_subordinates()
            employee.child_all_count = len(employee.subordinate_ids)

    @api.depends_context('uid', 'company')
    @api.depends('parent_id')
    def _compute_is_subordinate(self):
        subordinates = self.env.user.employee_id.subordinate_ids
        if not subordinates:
            self.is_subordinate = False
        else:
            for employee in self:
                employee.is_subordinate = employee.id in subordinates.ids

    def _search_is_subordinate(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        # Double negation
        if not value:
            operator = '!=' if operator == '=' else '='
        if not self.env.user.employee_id.subordinate_ids:
            return [('id', operator, self.env.user.employee_id.id)]
        return (['!'] if operator == '!=' else []) + [('id', 'in', self.env.user.employee_id.subordinate_ids.ids)]

    def _compute_child_count(self):
        employee_read_group = self._read_group(
            [('parent_id', 'in', self.ids)],
            ['parent_id'],
            ['id:count'],
        )
        child_count_per_parent_id = dict(employee_read_group)
        for employee in self:
            employee.child_count = child_count_per_parent_id.get(employee._origin, 0)
