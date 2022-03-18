# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    first_contract_date = fields.Date(related='employee_id.first_contract_date', groups="base.group_user")

    @api.model
    def _setup_fields(self):
        res = super()._setup_fields()
        self._fields['first_contract_date'].search = '_search_first_contract_date'
        return res

    def _search_first_contract_date(self, operator, value):
        return [('id', 'in', [res['id'] for res in self.env['hr.employee'].sudo().search_read([
                ('first_contract_date', operator, value)
            ])])]
