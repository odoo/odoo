# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_project_task_opened = fields.Boolean('Open Tasks')
    kpi_project_task_opened_value = fields.Integer(compute='_compute_project_task_opened_value', export_string_translation=False)

    def _compute_project_task_opened_value(self):
        if not self.env.user.has_group('project.group_project_user'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))

        self._calculate_company_based_kpi(
            'project.task',
            'kpi_project_task_opened_value',
            additional_domain=[('stage_id.fold', '=', False), ('project_id', '!=', False)],
        )

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_project_task_opened'] = 'project.open_view_project_all?menu_id=%s' % self.env.ref('project.menu_main_pm').id
        return res
