# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ReportProjectTaskUser(models.Model):
    _inherit = "report.project.task.user"

    hours_planned = fields.Float('Planned Hours', readonly=True)
    hours_effective = fields.Float('Effective Hours', readonly=True)
    remaining_hours = fields.Float('Remaining Hours', readonly=True)
    progress = fields.Float('Progress', group_operator='avg', readonly=True)
    overtime = fields.Float(readonly=True)

    def _select(self):
        select_to_append = """,
                (t.effective_hours * 100) / NULLIF(t.planned_hours, 0) as progress,
                t.effective_hours as hours_effective,
                t.planned_hours - t.effective_hours - t.subtask_effective_hours as remaining_hours,
                NULLIF(t.planned_hours, 0) as hours_planned,
                t.overtime as overtime
        """
        return super(ReportProjectTaskUser, self)._select() + select_to_append

    def _group_by(self):
        group_by_append = """,
                t.effective_hours,
                t.subtask_effective_hours,
                t.planned_hours,
                t.overtime
        """
        return super(ReportProjectTaskUser, self)._group_by() + group_by_append

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the time field labels according to the company timesheet encoding UOM
        makes the view cache dependent on the company timesheet encoding uom"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company.timesheet_encode_uom_id,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ['pivot', 'graph'] and self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            arch = self.env['account.analytic.line']._apply_time_label(arch, related_model=self._name)
        return arch, view
