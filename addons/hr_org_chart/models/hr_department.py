# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Department(models.Model):
    _inherit = "hr.department"

    has_read_access = fields.Boolean(search="_search_has_read_access", compute="_compute_has_read_access", store=False)

    def _search_has_read_access(self, operator, value):
        supported_operators = ["="]
        if operator not in supported_operators or not isinstance(value, bool):
            raise NotImplementedError()
        if not value:
            raise ValueError()
        if self.env.user.has_group('hr.group_hr_user'):
            return [(1, '=', 1)]
        departments_ids = self.env['hr.department'].sudo().search([
            '|',
            ('manager_id', 'in', self.env.user.employee_ids.ids),
            ('manager_id', 'in', self.env.user.employee_id.subordinate_ids.ids)]
        ).ids
        return [('id', 'child_of', departments_ids)]

    @api.depends_context('uid', 'company')
    @api.depends('manager_id')
    def _compute_has_read_access(self):
        if self.env.user.has_group('hr.group_hr_user'):
            for r in self:
                r.has_read_access = True
        else:
            departments_ids = self.env['hr.department'].sudo().search([
                '|',
                ('manager_id', 'in', self.env.user.employee_ids.ids),
                ('manager_id', 'in', self.env.user.employee_id.subordinate_ids.ids)]
            ).get_children_department_ids()
            for r in self:
                if r.id in departments_ids.ids:
                    r.has_read_access = True
                else:
                    r.has_read_access = False
