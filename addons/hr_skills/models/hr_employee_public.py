# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    current_employee_skill_ids = fields.One2many('hr.employee.skill', related='employee_id.current_employee_skill_ids')
    certification_ids = fields.One2many('hr.employee.skill', related='employee_id.certification_ids')
    display_certification_page = fields.Boolean(related="employee_id.display_certification_page")

    def _store_avatar_card_fields(self, res: Store.FieldList):
        super()._store_avatar_card_fields(res)
        res.many("employee_skill_ids", ["color", "display_name"])
