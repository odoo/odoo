# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Time Off Count", compute='_compute_associated_leaves_count')
    leave_accrual_plan_id = fields.Many2one(
        string="Accrual Plan",
        comodel_name="hr.leave.accrual.plan",
        index="btree_not_null",
        help="",
    )

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves']._read_group(
            [('resource_id', '=', False),
             '|',
                ('calendar_id', 'in', self.ids),
                '&',
                    ('calendar_id', '=', False),
                    ('company_id', 'in', self.company_id.ids + [False])],
            ['calendar_id', 'company_id'],
            ['__count'],
        )
        calendar_leaves = {}
        company_leaves = {}
        for calendar, company, count in leaves_read_group:
            if calendar:
                calendar_leaves[calendar.id] = calendar_leaves.get(calendar.id, 0) + count
            else:
                company_leaves[company.id] = company_leaves.get(company.id, 0) + count
        for calendar in self:
            calendar.associated_leaves_count = calendar_leaves.get(calendar.id, 0) + company_leaves.get(calendar.company_id.id, 0)

    def action_open_public_holidays(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'resource.calendar.leaves',
            'name': self.env._('Public Holidays'),
            'view_mode': 'list',
            'view_id': self.env.ref('hr_holidays.resource_calendar_leaves_tree_inherit').id,
            'domain': [
                ('resource_id', '=', False),
                '|',
                    ('calendar_id', '=', self.id),
                    '&',
                        ('calendar_id', '=', False),
                        ('company_id', 'in', self.company_id.ids + [False]),
            ],
            'context': {
                'default_calendar_id': self.id,
                'search_default_filter_date': True,
            },
            'search_view_id': self.env.ref('hr_holidays.resource_calendar_leaves_view_search_inherit').id,
        }
