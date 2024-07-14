# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nBeEcoVouchersWizard(models.TransientModel):
    _name = 'l10n.be.dimona.wizard'
    _description = 'Dimona Wizard'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    contract_id = fields.Many2one(
        'hr.contract', string='Contract',
        default=lambda self: self.env.context.get('active_id'))
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', related='contract_id.employee_id', readonly=True)
    employee_birthday = fields.Date(related='employee_id.birthday')
    contract_date_start = fields.Date(related='contract_id.date_start')
    contract_date_end = fields.Date(related='contract_id.date_end')
    contract_is_student = fields.Boolean(related='contract_id.l10n_be_is_student')
    contract_wage_type = fields.Selection(related='contract_id.wage_type')
    contract_country_code = fields.Char(related='contract_id.country_code')
    contract_planned_hours = fields.Integer(related='contract_id.l10n_be_dimona_planned_hours')
    without_niss = fields.Boolean(string="Employee Without NISS")

    declaration_type = fields.Selection(
        selection=[
            ('in', 'Register employee entrance'),
            ('out', 'Register employee departure'),
            ('update', 'Update employee information'),
            ('cancel', 'Cancel employee declaration')
        ], default='in')

    @api.depends('employee_id')
    def _compute_contract_id(self):
        for wizard in self:
            wizard.contract_id = wizard.employee_id.contract_id

    def submit_declaration(self):
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_('There is no contract defined on the employee form.'))
        if self.declaration_type == 'in':
            if self.contract_id.l10n_be_dimona_in_declaration_number:
                raise UserError(_('There is already a IN declaration for this contract.'))
            if self.contract_id.l10n_be_is_student:
                if not self.contract_id.l10n_be_dimona_planned_hours:
                    raise UserError(_('There is no defined planned hours on the student contract.'))
                if not self.contract_id.date_end:
                    raise UserError(_('There is no defined end date on the student contract.'))
                if (self.contract_id.date_end.month - 1) // 3 + 1 != (self.contract_id.date_start.month - 1) // 3 + 1:
                    raise UserError(_('Start date and end date should belong to the same quarter.'))
                if self.contract_id.date_start < fields.Date.today():
                    raise UserError(_('The DIMONA should be introduced before start date for students.'))
            self.contract_id._action_open_dimona(foreigner=self.without_niss)
        elif self.declaration_type == 'out':
            if not self.contract_date_end:
                raise UserError(_('There is not end date defined on the employee contract.'))
            self.contract_id._action_close_dimona()
        elif self.declaration_type == 'update':
            self.contract_id._action_update_dimona()
        elif self.declaration_type == 'cancel':
            self.contract_id._action_cancel_dimona()
        return {
            'name': self.employee_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract',
            'res_id': self.contract_id.id,
            'views': [(False, 'form')]
        }
