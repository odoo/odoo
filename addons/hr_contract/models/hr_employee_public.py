# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, SUPERUSER_ID


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    first_contract_date = fields.Date(related='employee_id.first_contract_date', groups="base.group_user")

    # Due to _search in HrEmployee calling HrEmployeePublic's _search, this lead to recursion as _search on
    # related field search on the original field.
    # TODO in master : Remove + change first_contract_date to `fields.Date()`,
    #  stored fields are handle in hr_employee_public
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if len(args) == 1 and args[0][0] == 'first_contract_date':
            return self.env['hr.employee'].sudo()._search(args, offset, limit, order, count, access_rights_uid)
        return super()._search(args, offset, limit, order, count, access_rights_uid)
