# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'
    _description = 'Salary Structure Type'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char('Structure Type', required=True)
    default_schedule_pay = fields.Selection([
        ('annually', 'Annually'),
        ('semi-annually', 'Semi-annually'),
        ('quarterly', 'Quarterly'),
        ('bi-monthly', 'Bi-monthly'),
        ('monthly', 'Monthly'),
        ('semi-monthly', 'Semi-monthly'),
        ('bi-weekly', 'Bi-weekly'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
    ], string='Default Scheduled Pay', default='monthly',
    help="Defines the frequency of the wage payment.")
    struct_ids = fields.One2many('hr.payroll.structure', 'type_id', string="Structures")
    default_struct_id = fields.Many2one('hr.payroll.structure', string="Regular Pay Structure")
    default_work_entry_type_id = fields.Many2one('hr.work.entry.type', help="Work entry type for regular attendances.", required=True,
                                                 default=lambda self: self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False))
    wage_type = fields.Selection([
        ('monthly', 'Fixed Wage'),
        ('hourly', 'Hourly Wage')
    ], string="Default Wage Type", default='monthly', required=True)
    struct_type_count = fields.Integer(compute='_compute_struct_type_count', string='Structure Type Count')

    def _compute_struct_type_count(self):
        for structure_type in self:
            structure_type.struct_type_count = len(structure_type.struct_ids)

    def _check_country(self, vals):
        country_id = vals.get('country_id')
        if country_id and country_id not in self.env.companies.mapped('country_id').ids:
            raise UserError(_('You should also be logged into a company in %s to set this country.', self.env['res.country'].browse(country_id).name))

    def write(self, vals):
        if self.env.context.get('payroll_check_country'):
            self._check_country(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('payroll_check_country'):
            for vals in vals_list:
                self._check_country(vals)
        return super().create(vals_list)
