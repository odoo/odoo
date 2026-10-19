# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_recruitment_new_colleagues = fields.Boolean('New Employees')
    kpi_hr_recruitment_new_colleagues_value = fields.Integer(compute='_compute_kpi_hr_recruitment_new_colleagues_value')

    def _compute_kpi_hr_recruitment_new_colleagues_value(self):
        self._raise_if_not_member_of('hr_recruitment.group_hr_recruitment_user')
        self._calculate_kpi(
            'hr.employee',
            'kpi_hr_recruitment_new_colleagues_value',
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('hr.menu_hr_root').id
        res['kpi_action']['kpi_hr_recruitment_new_colleagues'] = f'hr.open_view_employee_list_my?menu_id={menu_id}'
        res['kpi_sequence']['kpi_hr_recruitment_new_colleagues'] = 12500
        return res
