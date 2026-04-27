# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrPayrollDeclarationMixin(models.AbstractModel):
    _name = 'hr.payroll.declaration.mixin'
    _description = 'Payroll Declaration Mixin'

    @api.model
    def default_get(self, field_list=None):
        country_restriction = self._country_restriction()
        if country_restriction and self.env.company.country_id.code != country_restriction:
            raise UserError(_('You must be logged in a %s company to use this feature', country_restriction))
        return super().default_get(field_list)

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    year = fields.Selection(
        selection='_get_year_selection', string='Year', required=True,
        default=lambda x: str(datetime.now().year - 1))
    line_ids = fields.One2many(
        'hr.payroll.employee.declaration', 'res_id', string='Declarations')
    lines_count = fields.Integer(compute='_compute_lines_count')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    pdf_error = fields.Text('PDF Error Message')

    def unlink(self):
        self.line_ids.unlink()  # We need to unlink the child line_ids as well to prevent orphan records
        return super().unlink()

    def action_generate_declarations(self):
        for sheet in self:
            if not sheet.line_ids:
                raise UserError(_('There is no declaration to generate for the given period'))
        return self.action_generate_pdf()

    @api.depends('line_ids')
    def _compute_lines_count(self):
        for sheet in self:
            sheet.lines_count = len(sheet.line_ids)

    def action_open_declarations(self):
        self.ensure_one()
        return {
            'name': _('Employee Declarations'),
            'res_model': 'hr.payroll.employee.declaration',
            'type': 'ir.actions.act_window',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'domain': [('res_id', '=', self.id), ('res_model', '=', self._name)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def _country_restriction(self):
        return False

    def action_generate_pdf(self):
        return self.line_ids.action_generate_pdf()

    def _post_process_rendering_data_pdf(self, rendering_data):
        return rendering_data

    def _get_rendering_data(self, employees):
        return {}

    def _process_files(self, files):
        self.ensure_one()
        self.pdf_error = False
        for employee, filename, data in files:
            line = self.line_ids.filtered(lambda l: l.employee_id == employee)
            line.write({
                'pdf_file': base64.encodebytes(data),
                'pdf_filename': filename,
            })

    def _get_pdf_report(self):
        return False

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%(employee_name)s-declaration-%(year)s', employee_name=employee.legal_name, year=self.year)
