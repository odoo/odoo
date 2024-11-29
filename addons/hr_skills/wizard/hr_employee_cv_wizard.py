# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import _, api, fields, models


class HrEmployeeCvWizard(models.TransientModel):
    _name = 'hr.employee.cv.wizard'
    _description = 'Print Resume'

    employee_ids = fields.Many2many('hr.employee')

    color_primary = fields.Char('Primary Color', default=lambda self: self.env.company.primary_color or "#666666", required=True)
    color_secondary = fields.Char('Secondary Color', default=lambda self: self.env.company.secondary_color or "#666666", required=True)

    show_skills = fields.Boolean(string='Skills', default=True)
    show_contact = fields.Boolean(string='Contact Information', default=True)
    show_others = fields.Boolean(string='Others', default=True)

    can_show_others = fields.Boolean(compute='_compute_can_show_others')
    can_show_skills = fields.Boolean(compute='_compute_can_show_others')

    @api.depends('employee_ids')
    def _compute_can_show_others(self):
        for wizard in self:
            wizard.can_show_others = wizard.employee_ids.resume_line_ids.filtered(lambda l: not l.line_type_id)
            wizard.can_show_skills = wizard.employee_ids.skill_ids

    def action_validate(self):
        self.ensure_one()
        return {
            'name': _('Print Resume'),
            'type': 'ir.actions.act_url',
            'url': '/print/cv?' + url_encode({
                'employee_ids': ','.join(str(x) for x in self.employee_ids.ids),
                'color_primary': self.color_primary,
                'color_secondary': self.color_secondary,
                'show_skills': 1 if self.show_skills else None,
                'show_contact': 1 if self.show_contact else None,
                'show_others': 1 if self.show_others else None,
            })
        }
