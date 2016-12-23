# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import logging
import openerp.addons.decimal_precision as dp
from openerp.tools.safe_eval import safe_eval as eval
_logger = logging.getLogger(__name__)


class hr_ke_benefits_type(models.Model):
	_name = "ke.benefit.type"
	_description = "Benefit Type"
	_inherit = ["mail.thread"]
	_order = "name asc"

	name = fields.Char('Name of Benefit', required=True)
	code = fields.Char('Code', required=True, size=10, help="Enter a unique CODE that will be used to identify this benefit in the payslip")
	taxable = fields.Boolean('Taxable ?', default=True)
	formula = fields.Text('Formula')
	frequency = fields.Selection([('month', 'Monthly'),('day', 'Daily')], 'Frequency of Pay', required=True)
	rule_id = fields.Many2one('hr.salary.rule','Rule Number')
	sequence = fields.Integer('Sequence in Payslip', 
		help="This is the rule sequence to be used in payslip processing.For Benefits, put an integer between 20-29 inclusive", default=20)

	_defaults = {
	   'formula': '''
# Available variables:
#----------------------
# contract: hr.contract object
# Note: returned value have to be set in the variable 'result'
result = 0.00
'''
	}

	@api.multi
	def write(self, vals):
	    rule_vals = {}
	    for record in self:
	        if vals.get('code'):
                   vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
		   rule_vals.update({'code': vals.get('code'), 'amount_python_compute': self.ke_fetch_formula(vals.get('code'))})
	    res = super(hr_ke_benefits_type, self).write(vals)
	    for record in self:
	       if vals.get('formula'):#we need to ensure we update the affected benefits in the contracts when a formula is changed
	          for benefit in  record.env['ke.benefits'].search([('benefit_id', '=', record.id), ('computation', '=', 'formula')]):
		      benefit.compute_benefit()
		      for other_benefit in benefit.contract_id.benefits:#update other benefits within the same contract after formula change
			  if (other_benefit.benefit_id.id != record.id) and (other_benefit.computation == 'formula'):
				other_benefit.compute_benefit()
	    for record in self:
                if vals.get('name'):
		   rule_vals.update({'name': vals.get('name')})
		if vals.get('sequence'):
		   rule_vals.update({'sequence': vals.get('sequence')})
            self.env['hr.salary.rule'].browse([self.rule_id]).write(rule_vals)
	    return res

	@api.one
	@api.constrains('code')
	def check_code(self):
	    if self.search_count([('code', '=', self.code)]) > 1:
		raise ValidationError('A benefit with the same code [%s] already exist in the databse, \
                                       \nplease use a different code for this benefit' %self.code)

	def ke_fetch_formula(self, code):
	    return """
# Available variables:
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.
# Note: returned value have to be set in the variable 'result'
result = contract.benefits.search([('code', '=', '""" + code + """' ), ('contract_id', '=', contract.id)]).amount
"""

               

	@api.model
	def create(self, vals):
	    vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
	    benefit = super(hr_ke_benefits_type, self).create(vals)
	    rule_vals = {
	     'name': benefit.name,
	     'category_id': self.env['hr.salary.rule.category'].search([('code', '=', 'BENEFITS')])[0].id,
	     'code': benefit.code,
	     'sequence': benefit.sequence,
	     'active': True,
	     'appears_on_payslip': True,
	     'condition_select': 'none',
	     'amount_select': 'code',
	     'amount_python_compute': self.ke_fetch_formula(benefit.code)
	    }
	    rule = self.env['hr.salary.rule'].create(rule_vals)
	    benefit.write({'rule_id': rule.id})
	    return benefit

	@api.multi
	def unlink(self):
	    for record in self:
		record.rule_id.unlink()
	    return super(hr_ke_benefits_type, self).unlink()

class hr_ke_earnings_type(models.Model):
	_name = "ke.earnings.type"
	_description = "Earnings Type"
	_inherit = ["mail.thread"]
	_order = "name asc"

	name = fields.Char('Name of Earning', required=True)
	code = fields.Char('Code', required=True, size=10, help="Enter a unique CODE that will be used to identify this earning in the payslip")
	taxable = fields.Boolean('Taxable ?', default=True)
	formula = fields.Text('Formula')
	frequency = fields.Selection([('month', 'Monthly'),('day', 'Daily')], 'Frequency of Pay', required=True)
	rule_id = fields.Many2one('hr.salary.rule','Rule Number')
	sequence = fields.Integer('Sequence in Payslip', 
		help="This is the rule sequence to be used in payslip processing.For Earnings, put an integer between 5-9 inclusive", default=5)


        _defaults = {
           'formula': '''
# Available variables:
#----------------------
# contract: hr.contract object
# Note: returned value have to be set in the variable 'result'
result = 0.00
'''
        }

        @api.multi
        def write(self, vals):
	    rule_vals = {}
	    for record in self:
	        if vals.get('code'):
                   vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
		   rule_vals.update({'code': vals.get('code'), 'amount_python_compute': self.ke_fetch_formula(vals.get('code'))})
            res = super(hr_ke_earnings_type, self).write(vals)
	    for record in self:
                if vals.get('formula'):#we need to ensure we update the affected earnings in the contracts when a formula is changed
                  for earning in  record.env['ke.earnings'].search([('earning_id', '=', record.id), ('computation', '=', 'formula')]):
                      earning.compute_earning()
                      for other_earning in earning.contract_id.earnings:#update other benefits within the same contract after formula change
                          if (other_earning.earning_id.id != record.id) and (other_earning.computation == 'formula'):
                                other_earning.compute_earning()

	    for record in self:
                if vals.get('name'):
		   rule_vals.update({'name': vals.get('name')})
		if vals.get('sequence'):
		   rule_vals.update({'sequence': vals.get('sequence')})
            self.env['hr.salary.rule'].browse([self.rule_id]).write(rule_vals)
            return res


	@api.one
	@api.constrains('code')
	def check_code(self):
	    if self.search_count([('code', '=', self.code)]) > 1:
		raise ValidationError('An Earning with the same code [%s] already exist in the databse, \
					please use a different code' %self.code)

	@api.model
	def create(self, vals):
	    vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
	    res = super(hr_ke_earnings_type, self).create(vals)
	    rule_vals = {
	     'name': res.name,
	     'category_id': self.env['hr.salary.rule.category'].search([('code', '=', 'CASH_ALW')])[0].id,
	     'code': res.code,
	     'sequence': res.sequence,
	     'active': True,
	     'appears_on_payslip': True,
	     'condition_select': 'none',
	     'amount_select': 'code',
	     'amount_python_compute': self.ke_fetch_formula(res.code)
	    }
	    rule = self.env['hr.salary.rule'].create(rule_vals)
	    res.write({'rule_id': rule.id})
	    return res


	@api.multi
	def unlink(self):
	    for record in self:
		record.rule_id.unlink()
	    return super(hr_ke_earnings_type, self).unlink()

	def ke_fetch_formula(self, code):
	    return """
# Available variables:
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.
# Note: returned value have to be set in the variable 'result'
result = contract.earnings.search([('code', '=', '""" + code + """' ), ('contract_id', '=', contract.id)]).amount
"""
	

class hr_ke_relief_type(models.Model):
	_name = "ke.relief.type"
        _description = "Tax Relief Type"
        _inherit = ["mail.thread"]
        _order = "name asc"

	name = fields.Char('Name of Relief', required=True)
	code = fields.Char('Code', required=True, size=10, help="Enter a unique CODE that will be used to identify this Tax Relief type in the payslip")
	formula = formula = fields.Text('Formula')
	frequency = fields.Selection([('month', 'Monthly'),('day', 'Daily')], 'Frequency of Deduction', required=True)
	rule_id = fields.Many2one('hr.salary.rule','Rule Number')
	sequence = fields.Integer('Sequence in Payslip', 
		help="This is the rule sequence to be used in payslip processing.For Tax reliefs, put an integer between 65-69 inclusive", default=65)

	
        _defaults = {
           'formula': '''
# Available variables:
#----------------------
# contract: hr.contract object
# Note: returned value have to be set in the variable 'result'
result = 0.00
'''
	}

	@api.multi
	def write(self, vals):
	    rule_vals = {}
	    for record in self:
	        if vals.get('code'):
                   vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
		   rule_vals.update({'code': vals.get('code'), 'amount_python_compute': self.ke_fetch_formula(vals.get('code'))})
	    res = super(hr_ke_relief_type, self).write(vals)
	    for record in self:
		if vals.get('formula'):
		   for relief in record.env['ke.reliefs'].search([('relief_id', '=', record.id), ('computation', '=', 'formula')]):
			relief.compute_relief()
	    for record in self:
                if vals.get('name'):
		   rule_vals.update({'name': vals.get('name')})
		if vals.get('sequence'):
		   rule_vals.update({'sequence': vals.get('sequence')})
            self.env['hr.salary.rule'].browse([self.rule_id]).write(rule_vals)
            return res		

	@api.one
	@api.constrains('code')
	def check_code(self):
	    if self.search_count([('code', '=', self.code)]) > 1:
		raise ValidationError('A Tax Relief with the same code [%s] already exist in the databse, \
					please use a different code' %self.code)

	@api.model
	def create(self, vals):
	    vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
	    res = super(hr_ke_relief_type, self).create(vals)
	    rule_vals = {
	     'name': res.name,
	     'category_id': self.env['hr.salary.rule.category'].search([('code', '=', 'TAX_RELIEF')])[0].id,
	     'code': res.code,
	     'sequence': res.sequence,
	     'active': True,
	     'appears_on_payslip': True,
	     'condition_select': 'none',
	     'amount_select': 'code',
	     'amount_python_compute': self.ke_fetch_formula(res.code)
	    }
	    rule = self.env['hr.salary.rule'].create(rule_vals)
	    res.write({'rule_id': rule.id})
	    return res


	@api.multi
	def unlink(self):
	    for record in self:
		record.rule_id.unlink()
	    return super(hr_ke_relief_type, self).unlink()

	def ke_fetch_formula(self, code):
	    return """
# Available variables:
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.
# Note: returned value have to be set in the variable 'result'
result = employee.reliefs.search([('code', '=', '""" + code + """' ), ('employee_id', '=', employee.id)]).amount
"""

class hr_ke_deductions_type(models.Model):
	_name = "ke.deductions.type"
        _description = "Deductions Type"
        _inherit = ["mail.thread"]
        _order = "name asc"

	name = fields.Char('Name of Deduction', required=True)
	code = fields.Char('Code', required=True, size=10, help="Enter a unique CODE that will be used to identify this deduction in the payslip")
	pre_tax = fields.Boolean('Pre-Tax Deduction ?', default=False)
	net_pay = fields.Boolean('Deduct from Net-Pay ?', default=False)
	frequency = fields.Selection([('month', 'Monthly'),('day', 'Daily')], 'Frequency of Deduction', required=True)
	formula = formula = fields.Text('Formula')
	rule_id = fields.Many2one('hr.salary.rule','Rule Number')
	sequence = fields.Integer('Sequence in Payslip', 
		help="This is the rule sequence to be used in payslip processing.For Pre-tax Deductions, put an integer between 40-49 inclusive. For Post-Tax Deduction use interger between 80-89 inclusive", required=True)

	
        _defaults = {
           'formula': '''
# Available variables:
#----------------------
# employee: hr.employee object
# Note: returned value have to be set in the variable 'result'
result = 0.00
'''
        }

	@api.one
	@api.onchange('pre_tax')
	def return_seq(self):
	    if self.pre_tax:
		self.sequence = 40
	    else:
		self.sequence = 80	

	@api.multi
	def write(self, vals):
	    rule_vals = {}    
	    for record in self:
	        if vals.get('code'):
                   vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
        	   rule_vals.update({'code': vals.get('code'), 'amount_python_compute': self.ke_fetch_formula(vals.get('code'))})
	    res = super(hr_ke_deductions_type, self).write(vals)
	    for record in self:
		if vals.get('formula'):
		   for deduction in record.env['ke.deductions'].search([('deduction_id', '=', record.id), ('computation', '=', 'formula1')]):
			deduction.compute_deduction()
	    for record in self:
                if vals.get('name'):
		   rule_vals.update({'name': vals.get('name')})
		if vals.get('sequence'):
		   rule_vals.update({'sequence': vals.get('sequence')})
            self.env['hr.salary.rule'].browse([self.rule_id]).write(rule_vals)
            return res		

	@api.one
	@api.constrains('code')
	def check_code(self):
	    if self.search_count([('code', '=', self.code)]) > 1:
		raise ValidationError('A deduction with the same code [%s] already exist in the databse, \
					please use a different code' %self.code)

	@api.model
	def create(self, vals):
	    vals.update({'code': ''.join(vals.get('code').split())}) # remove all whitespaces in the code
	    res = super(hr_ke_deductions_type, self).create(vals)
	    if res.pre_tax:
		cd = 'PRE_TAX_DED'
	    else:
		cd = 'POST_TAX_DED'
	    rule_vals = {
	     'name': res.name,
	     'category_id': self.env['hr.salary.rule.category'].search([('code', '=', cd)])[0].id,
	     'code': res.code,
	     'sequence': res.sequence,
	     'active': True,
	     'appears_on_payslip': True,
	     'condition_select': 'none',
	     'amount_select': 'code',
	     'amount_python_compute': self.ke_fetch_formula(res.code)
	    }
	    rule = self.env['hr.salary.rule'].create(rule_vals)
	    res.write({'rule_id': rule.id})
	    return res


	@api.multi
	def unlink(self):
	    for record in self:
		record.rule_id.unlink()
	    return super(hr_ke_deductions_type, self).unlink()

	def ke_fetch_formula(self, code):
	    return """
# Available variables:
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.
# Note: returned value have to be set in the variable 'result'
result = employee.deductions.search([('code', '=', '""" + code + """' ), ('employee_id', '=', employee.id)]).amount
"""

class hr_ke_tax_relief(models.Model):
        _name = "ke.reliefs"
        _description = "Tax Relief"
        _inherit = ["mail.thread"]
        _order = "employee_id, name asc"

        @api.one
        @api.depends('write_date')
        def compute_name(self):
            self.name = str(self.relief_id.name) + ' (' + str(self.employee_id.name) + ')'

        @api.one
        @api.depends('computation', 'fixed', 'base')
        def compute_relief(self):
            if self.computation == 'fixed':
                self.amount = self.fixed
            elif self.computation == 'formula':
                baselocaldict ={'result': None, 'employee': self.employee_id, 'relief': self}
                localdict = dict(baselocaldict)
                try:
                    eval(self.relief_id.formula, localdict, mode='exec', nocopy=True)
                except:
                    raise except_orm(_('Error!'), _('Wrong formula defined for this Relief: %s (%s).')% (self.relief_id.name, self.relief_id.formula))
                self.amount = localdict['result']
            else:
                self.amount = 0.00

        name = fields.Char('Name of Relief', compute='compute_name', store=True)
	relief_id = fields.Many2one('ke.relief.type', 'Type of Relief', required=True)
	employee_id = fields.Many2one('hr.employee', 'Employee Name', required=True)
	code = fields.Char('Code', related='relief_id.code')
	fixed = fields.Float('Fixed Value', digits=dp.get_precision('Account'))
        amount = fields.Float('Total Relief', compute='compute_relief', digits=dp.get_precision('Account'), store=True)
	base = fields.Float('Base Value', digits=dp.get_precision('Account'), required=True,
                        help="Enter the 'Base' value that will be used to compute the actual relief for the employee...\
			E.g for Insurance Relief, you enter the annuel premium value to be used to compute the monthly relief \
			using the predefined formula as prescribed in the PAYE guide issued by KRA")
	computation = fields.Selection([('fixed', 'Use Fixed Value'),('formula', 'Use Predefined Formula')], 'Computation Method', required=True)
	
	@api.one
	@api.constrains('employee_id', 'amount')
	def check_ducplicates(self):
	    if self.search_count([('code', '=', self.code), ('employee_id', '=', self.employee_id.id)]) > 1:
		raise ValidationError("Duplicate '%s' for %s!"%(self.relief_id.name, self.employee_id.name))
	    if self.amount <= 0:
		raise ValidationError("Only posistive and non-zero values are accepted for %s" %self.relief_id.name)

class hr_ke_deductions(models.Model):

	_name = "ke.deductions"
        _description = "Deductions"
        _inherit = ["mail.thread"]
        _order = "id, name asc"

	@api.one
        @api.depends('write_date')
	def compute_name(self):
            self.name = str(self.deduction_id.name) + ' (' + str(self.employee_id.name) + ')'

	@api.one
        @api.depends('computation', 'fixed', 'base')
        def compute_deduction(self):
            if self.computation == 'fixed':
                self.amount = self.fixed
            elif self.computation == 'formula1':
		if self.env.context.get('default_employee_id'):
		   contracts = self.env['hr.contract'].search([('employee_id', '=', self.env.context.get('default_employee_id'))])
		   if not contracts:
			raise except_orm(_('Error!'),_('No contract defined for this Employee!'))
		else:
		   contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
		   if not contracts:
			raise except_orm(_('Error!'),_('No contract defined for %s'%self.employee_id.name))
		   
                baselocaldict ={'result': None, 'employee': self.employee_id, 'deduction': self, 'contract': contracts[0]}
                localdict = dict(baselocaldict)
                try:
                    eval(self.deduction_id.formula, localdict, mode='exec', nocopy=True)
                except:
                    raise except_orm(_('Error!'), _('Error in general formula defined for this deduction: %s (%s).')% (self.deduction_id.name, self.deduction_id.formula))
                self.amount = localdict['result']
		
	    elif self.computation == 'formula2':
	        baselocaldict ={'result': None, 'employee': self.employee_id, 'deduction': self}	
                localdict = dict(baselocaldict)
                try:
                    eval(self.formula, localdict, mode='exec', nocopy=True)
                except:
                    raise except_orm(_('Error!'), _('Error in Employee formula defined for this deduction: %s (%s).')% (self.name, self.formula))
                self.amount = localdict['result']
            else:
                self.amount = 0.00


	name = fields.Char('Name', compute='compute_name', store=True)
	deduction_id = fields.Many2one('ke.deductions.type', 'Type of Deduction', required=True)
	employee_id = fields.Many2one('hr.employee', 'Employee Name', required=True)
	code = fields.Char('Code', related='deduction_id.code')
	fixed = fields.Float('Fixed Amount', digits=dp.get_precision('Account'))
	computation = fields.Selection([('fixed', 'Fixed Amount'),('formula1', 'Use General Formula'), ('formula2', 'Use Employee Formula')], 'Computation Method', required=True)
	amount = fields.Float('Amount to Deduct', compute='compute_deduction', digits=dp.get_precision('Account'), store=True)
	base = fields.Float('Actual Value', digits=dp.get_precision('Account'), required=True,default=0.00,
                        help="This is the actual Cost/Contribution that the employee is making. E.g if its towards a defined pension scheme fund, then enter the actual monthly contribution. Depending on how the deductable amount is computed, this field my not be necessary and can be left out.")
	formula = formula = fields.Text('Formula', help="You can define an employee specific formula for computing a deduction to be made on his/her salary. This is useful for voluntary deductions such as SACCO/CHAMA contributions")
        _defaults = {
           'formula': '''
# Available variables:
#----------------------
# employee: hr.employee object
# Note: returned value have to be set in the variable 'result'
result = 0.00
'''
        }

	@api.one
	@api.constrains('employee_id', 'amount')
	def check_ducplicates(self):
	    if self.search_count([('code', '=', self.code), ('employee_id', '=', self.employee_id.id)]) > 1:
		raise ValidationError("Duplicate '%s' for %s!"%(self.deduction_id.name, self.employee_id.name))
	    if self.amount <= 0:
		raise ValidationError("Only posistive and non-zero values are accepted for %s" %self.deduction_id.name)

class hr_ke_benefits(models.Model):
	_name = "ke.benefits"
        _description = "Benefits"
        _inherit = ["mail.thread"]
        _order = "contract_id, name asc"

	@api.one
	@api.depends('computation', 'fixed', 'actual_cost')
	def compute_benefit(self):
	    if self.computation == 'fixed':
		self.amount = self.fixed
	    elif self.computation == 'formula':
		baselocaldict ={'result': None, 'contract': self.contract_id, 'benefit': self}
		localdict = dict(baselocaldict)
		try:
                    eval(self.benefit_id.formula, localdict, mode='exec', nocopy=True)
            	except:
                    raise except_orm(_('Error!'), _('Wrong formula defined for this benefit: %s (%s).')% (self.benefit_id.name, self.benefit_id.formula))
		self.amount = localdict['result']
	    else:
		self.amount = 0.00

	@api.one
	@api.depends('write_date')
	def compute_name(self):
	    self.name = str(self.benefit_id.name) + ' (' + str(self.contract_id.name) + ')'

	name = fields.Char('Name', compute='compute_name', store=True)
	benefit_id = fields.Many2one('ke.benefit.type', 'Type of Benefit', required=True)
	code = fields.Char('Code', related='benefit_id.code', store=True)
	contract_id = fields.Many2one('hr.contract', 'Contract', required=True) 
	amount = fields.Float('Taxable Value', compute='compute_benefit', digits=dp.get_precision('Account'), store=True)
	computation = fields.Selection([('fixed', 'Use Fixed Value'),('formula', 'Use Predefined Formula')], 'Computation Method', required=True)
	actual_cost = fields.Float('Actual Cost', digits=dp.get_precision('Account'), required=True,
			help="Enter the cost value of this benefit that will be used to compute the taxable value to be charged against employee as tax. E.g if its rented 				Housing, enter the amount to pay as rent on monthly basis")
	fixed = fields.Float('Fixed Value', digits=dp.get_precision('Account'))


	@api.one
	@api.constrains('contract_id', 'amount')
	def check_ducplicates(self):
	    if self.search_count([('code', '=', self.code), ('contract_id', '=', self.contract_id.id)]) > 1:
		raise ValidationError("Duplicate '%s' for %s!"%(self.benefit_id.name, self.contract_id.name))
	    if self.amount <= 0:
		raise ValidationError("Only posistive and non-zero values are accepted for %s" %self.benefit_id.name)

class hr_ke_earnings(models.Model):
        _name = "ke.earnings"
        _description = "Other Earnings (cash)"
        _inherit = ["mail.thread"]
        _order = "contract_id asc"
	
        @api.one
        @api.depends('computation', 'fixed')
        def compute_earning(self):
            if self.computation == 'fixed':
                self.amount = self.fixed
            elif self.computation == 'formula':
                baselocaldict ={'result': None, 'contract': self.contract_id}
                localdict = dict(baselocaldict)
                try:
                    eval(self.earning_id.formula, localdict, mode='exec', nocopy=True)
                except:
                    raise except_orm(_('Error!'), _('Wrong formula defined for Other Earnings (cash): %s (%s).')% (self.earning_id.name, self.earning_id.formula))
                self.amount = localdict['result']

            else:
                self.amount = 0.00

        @api.one
        @api.depends('write_date')
        def compute_name(self):
            self.name = str(self.earning_id.name) + ' (' + str(self.contract_id.name) + ')'


        name = fields.Char('Name', compute='compute_name', store=True)
        earning_id = fields.Many2one('ke.earnings.type', 'Type of Earning', required=True)
	code = fields.Char('Code', related='earning_id.code')
        contract_id = fields.Many2one('hr.contract', 'Contract', required=True)
        amount = fields.Float('Taxable Value', compute='compute_earning', digits=dp.get_precision('Account'), store=True)
        computation = fields.Selection([('fixed', 'Use Fixed Value'),('formula', 'Use Predefined Formula')], 'Computation Method', required=True)
        fixed = fields.Float('Fixed Value', digits=dp.get_precision('Account'))


	@api.one
	@api.constrains('contract_id', 'amount')
	def check_ducplicates(self):
	    if self.search_count([('code', '=', self.code), ('contract_id', '=', self.contract_id.id)]) > 1:
		raise ValidationError("Duplicate '%s' for %s!"%(self.earning_id.name, self.contract_id.name))
	    if self.amount <= 0:
		raise ValidationError("Only posistive and non-zero values are accepted for %s" %self.earning_id.name)

class hr_ke_relation_type(models.Model):
	_name = "ke.relation.type"
	_description = "Relation Type"
	_order = "name asc"
	_inherit = ["mail.thread"]
	
	name = fields.Char('Name')
	medical = fields.Boolean('Medical Beneficiary?', default=False)

class hr_ke_kins(models.Model):
	_description = "Employee Kin"
	_name = "ke.employee.kin"
	_order = "name asc"
	_inherit = ["mail.thread"]

	name = fields.Char('Name', required=True)
	birthday = fields.Date('Date of Birth')
	gender= fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender', required=True)
	phone = fields.Char('Phone Number')
	kin = fields.Boolean('Is Next of Kin?', default=False)
	relation = fields.Many2one('ke.relation.type', 'Type of Relation', required=True)
	address = fields.Text('Next of Kin Address')
	employee_id = fields.Many2one('hr.employee', 'Employee', required=True)

class hr_ke_employee(models.Model):
        _inherit = ["hr.employee"]

	@api.one
	@api.depends('write_date')
	def compute_employee_number(self):
	    self.employee_no = str(self.id).zfill(4)
        #residential Address
        house = fields.Char('House No', required=True)
        street =fields.Char('Estate/Apartment Name', required=True)
        suburb = fields.Char('Suburb', required=True)
        town = fields.Char('Town/City', required=True)
        box = fields.Char('Postal Address')
        home_tel = fields.Char('Home Telephone')
        box_code = fields.Char('Postal Code')
        box_town = fields.Char('Postal Town')
        # Kenya payroll details
	deduct_nhif = fields.Boolean('Deduct NHIF ?', default=True)
        nhif = fields.Char('NHIF No.')
	deduct_nssf = fields.Boolean('Deduct NSSF ?', default=True)
        nssf = fields.Char('NSSF No.')
        helb = fields.Boolean('HELB Loan ?', default=False)
        helb_rate = fields.Float('HELB Monthly Amount', digits=dp.get_precision('Account'))
	deduct_paye = fields.Boolean('Deduct PAYE ?', default=True)
        tax_pin = fields.Char('PAYE Tax PIN')
        # Others
        birth_country = fields.Many2one('res.country', 'Country of Birth')
	kins = fields.One2many('ke.employee.kin', 'employee_id', 'Dependants')
	employee_no = fields.Char('Employee Number', compute='compute_employee_number', store=True)
	personal_email = fields.Char('Personal Email')
	deductions = fields.One2many('ke.deductions', 'employee_id', 'Deductions')
	reliefs = fields.One2many('ke.reliefs', 'employee_id', 'Tax Relief')
	#disability Tax Excepmtion
	disability = fields.Boolean('Disabled ?', default=False)
	disability_rate = fields.Float('Disability Excempt Amount', digits=dp.get_precision('Account'))
	disability_cert = fields.Char('Disability Cert No', 
		help="This Requires approval from Kenya Revenue Autority and an excempt certificate must be produced by a person with disability as a proof")


class hr_ke_contract(models.Model):
        _inherit = ["hr.contract"]

	benefits = fields.One2many('ke.benefits', 'contract_id', 'Benefits')
	earnings = fields.One2many('ke.earnings', 'contract_id', 'Earnings')

	@api.multi
	def write(self, vals):
	    res = super(hr_ke_contract, self).write(vals)
	    for record in self:
	        if vals.get('wage'):
		   for earning in self.earnings:
		       earning.compute_earning()
	           for benefit in self.benefits:
	               benefit.compute_benefit()
	           for deduction in self.employee_id.deductions:
		       deduction.compute_deduction()
	    return res
	

        @api.one
        @api.onchange('benefits')
        def recompute(self):
	    for earning in self.earnings:
                earning.compute_earning()
            for benefit in self.benefits:
                benefit.compute_benefit()
	    for deduction in self.employee_id.deductions:
                deduction.compute_deduction()

	@api.one
	@api.constrains('wage')
	def ke_validate_values(self):
	    if self.wage <= 0:
		raise ValidationError("On positive and non-zero values are accepted for salaries or wages")

class ke_hr_payslip(models.Model):
	_inherit = ["hr.payslip"]

	
	def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
	    lines = super(ke_hr_payslip, self).get_payslip_lines(cr, uid, contract_ids, payslip_id, context=context)
	    return lines
