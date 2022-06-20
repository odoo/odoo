# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_project_task_opened = fields.Boolean('Open Tasks')
    kpi_project_task_opened_value = fields.Integer(compute='_compute_project_task_opened_value', export_string_translation=False)

    def _compute_project_task_opened_value(self):
        self._raise_if_not_member_of('project.group_project_user')
        self._calculate_kpi(
            'project.task',
            'kpi_project_task_opened_value',
            additional_domain=[('stage_id.fold', '=', False), ('project_id', '!=', False)],
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('project.menu_main_pm').id
        res['kpi_action']['kpi_project_task_opened'] = f'project.open_view_project_all?menu_id={menu_id}'
        res['kpi_sequence']['kpi_project_task_opened'] = 7500
        return res
