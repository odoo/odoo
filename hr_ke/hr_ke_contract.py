# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class hr_ke_contract_type(models.Model):
	_name = "hr.contract.type"
	_inherit = "hr.contract.type"

	rem_type = fields.Selection([('monthly', 'Monthly Rate'), ('hourly', 'Per Hour Rate'), ('daily', 'Per Day Rate')], 'Remuneration Type', required=True, default = 'monthly')

class hr_ke_contract(models.Model):
        _name = "hr.contract"
        _inherit = "hr.contract"

	wage = fields.Float('Remuneration Rate', digits=(32,2), required=True, help="Rate used to pay the salary of employee, could be monthly rate, hourly rate or daily rate depending on the contract type")
	rem_type = fields.Selection(related="type_id.rem_type", readonly=True )
	struct_id = fields.Many2one('hr.payroll.structure', 'Salary Structure', domain= "[('rem_type', '=', rem_type)]", help="Here you choose the right salary structure to use to determine the pay for employee with this contract. Choose the structure with the same remuneration type as the contract")
