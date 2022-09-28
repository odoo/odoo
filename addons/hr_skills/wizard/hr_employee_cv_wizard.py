# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import fields, models


class HrEmployeeCVWizard(models.TransientModel):
    _name = 'hr.employee.cv.wizard'
    _description = 'Print CV'

    employee_ids = fields.Many2many('hr.employee')
    color = fields.Char('Color Theme', default="#3a9bc8", required=True)
    side_panel_position = fields.Selection([('left', 'Left'), ('right', 'Right')], default='right', required=True)

    def action_validate(self):
        self.ensure_one()
        return {
            'name': 'Print CV',
            'type': 'ir.actions.act_url',
            'url': '/print/cv?' + url_encode({
                'employee_ids': ','.join(str(x) for x in self.employee_ids.ids),
                'color': self.color,
                'side_panel_position': self.side_panel_position,
            })
        }
