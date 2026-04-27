# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

MODELS_MAPPED = {'employee': 'hr.employee', 'bank_account': 'res.partner.bank'}


class HrContractSalaryPersonalInfo(models.Model):
    _name = 'hr.contract.salary.personal.info'
    _description = 'Salary Package Personal Info'
    _order = 'sequence'

    name = fields.Char(translate=True, required=True)
    sequence = fields.Integer(default=100)
    res_field_id = fields.Many2one(
        'ir.model.fields', string="Related Field",
        domain="[('model', '=', res_model), ('ttype', 'not in', ('one2many', 'many2one', 'many2many'))]", required=True, ondelete='cascade',
        help="Name of the field related to this personal info.")
    field = fields.Char(related='res_field_id.name', readonly=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    placeholder = fields.Char(translate=True)
    helper = fields.Char(translate=True)
    display_type = fields.Selection([
        ('text', 'Text'),
        ('radio', 'Radio'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date'),
        ('dropdown', 'Selection'),
        ('integer', 'Integer'),
        ('email', 'Email'),
        ('document', 'Document'),
    ], default='text')
    info_type_id = fields.Many2one('hr.contract.salary.personal.info.type', required=True)
    is_required = fields.Boolean(default=True)
    position = fields.Selection([
        ('left', 'Main Panel'),
        ('right', 'Side Panel'),
    ], default='left')
    value_ids = fields.One2many('hr.contract.salary.personal.info.value', 'personal_info_id')
    applies_on = fields.Selection([
        ('employee', 'Employee'),
        ('bank_account', 'Bank Account')
    ], default='employee')
    res_model = fields.Char(compute='_compute_res_model')
    impacts_net_salary = fields.Boolean(help=" If checked, any change on this information will trigger a new computation of the gross-->net salary.")
    dropdown_selection = fields.Selection([
        ('specific', 'Specific Values'),
        ('country', 'Countries'),
        ('state', 'States'),
        ('lang', 'Languages'),
    ], string="Selection Nature")
    parent_id = fields.Many2one('hr.contract.salary.personal.info')
    child_ids = fields.One2many('hr.contract.salary.personal.info', 'parent_id')

    @api.onchange('applies_on')
    def _onchange_applies_on(self):
        self.res_field_id = False

    @api.constrains('res_field_id', 'applies_on')
    def _check_res_field_model(self):
        for info in self:
            if info.res_field_id.model != MODELS_MAPPED.get(info.applies_on):
                raise ValidationError(_(
                    'Mismatch between res_field_id %(field)s and model %(model)s for info %(personal_info)s',
                    field=info.res_field_id.name,
                    model=MODELS_MAPPED.get(info.applies_on),
                    personal_info=info.name
                ))

    @api.depends('applies_on')
    def _compute_res_model(self):
        for info in self:
            info.res_model = MODELS_MAPPED.get(info.applies_on)

    def _hide_children(self, contract):
        self.ensure_one()
        for info in self:
            if not info.child_ids:
                return False
            if info.applies_on == 'employee':
                info_value = contract.employee_id[info.field]
            else:
                info_value = contract.employee_id.bank_account_id[info.field]
            if info.value_ids:
                value = info.value_ids.filtered(lambda v: v.value == info_value)
                return value.hide_children
            return not bool(info_value)

class HrContractSalaryPersonalInfoType(models.Model):
    _name = 'hr.contract.salary.personal.info.type'
    _description = 'Salary Package Personal Info Type'
    _order = 'sequence'

    name = fields.Char()
    sequence = fields.Integer(default=100)


class HrContractSalaryPersonalInfoValue(models.Model):
    _name = 'hr.contract.salary.personal.info.value'
    _description = 'Salary Package Personal Info Value'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=100)
    personal_info_id = fields.Many2one('hr.contract.salary.personal.info')
    value = fields.Char(required=True)
    hide_children = fields.Boolean(help="Hide children personal info when checked.")
