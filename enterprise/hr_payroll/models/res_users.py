# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

HR_PAYROLL_WRITABLE_FIELDS = [
    'is_non_resident',
]

class ResUsers(models.Model):
    _inherit = "res.users"

    is_non_resident = fields.Boolean(related='employee_ids.is_non_resident', readonly=False)

    def _get_personal_info_partner_ids_to_notify(self, employee):
        if employee.contract_id.hr_responsible_id:
            return (
                _("You are receiving this message because you are the HR Responsible of this employee."),
                employee.contract_id.hr_responsible_id.partner_id.ids,
            )
        return ('', [])

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + HR_PAYROLL_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + HR_PAYROLL_WRITABLE_FIELDS
