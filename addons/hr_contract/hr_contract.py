from osv import fields, osv

class hr_employee_marital_status(osv.osv):
	_name = "hr.employee.marital.status"
	_description = "Employee Marital Status"
	_columns = {
		'name' : fields.char('Marital Status', size=30, required=True),
		'description' : fields.text('Status Description'),
	}
hr_employee_marital_status()

class hr_employee(osv.osv):
	_name = "hr.employee"
	_description = "Employee"
	_inherit = "hr.employee"
	_columns = {
		'manager' : fields.boolean('Manager'),
		'soc_security' : fields.char('Social security number', size=50, select=True),
		'medic_exam' : fields.date('Medical examination date'),
		'audiens_num' : fields.char('AUDIENS Number', size=30),
		'nationality' : fields.many2one('res.country', 'Nationality'),
		'birth_date' : fields.date('Birth Date'),
		'place_of_birth' : fields.char('Place of Birth', size=30),
		'marital_status' : fields.many2one('hr.employee.marital.status', 'Marital Status'),
		'children' : fields.integer('Number of children'),
		'contract_ids' : fields.one2many('hr.contract', 'employee_id', 'Contracts'),
	}
hr_employee()

#Contract wage type period name
class hr_contract_wage_type_period(osv.osv):
	_name='hr.contract.wage.type.period'
	_description='Wage Period'
	_columns = {
		'name' : fields.char('Period Name', size=50, required=True, select=True),
	}
hr_contract_wage_type_period()

#Contract wage type (hourly, daily, monthly, ...)
class hr_contract_wage_type(osv.osv):
	_name = 'hr.contract.wage.type'
	_description = 'Wage Type'
	_columns = {
		'name' : fields.char('Wage Type Name', size=50, required=True, select=True),
		'period_id' : fields.many2one('hr.contract.wage.type.period', 'Wage Period', required=True),
		'type' : fields.selection([('gross','Gross'), ('net','Net')], 'Type', required=True),
	}
	_defaults = {
		'type' : lambda *a : 'gross',
	}
hr_contract_wage_type()

class hr_contract(osv.osv):
	_name = 'hr.contract'
	_description = 'Contract'
	_columns = {
		'name' : fields.char('Contract Name', size=30, required=True),
		'employee_id' : fields.many2one('hr.employee', 'Employee', required=True),
		'function' : fields.many2one('res.partner.function', 'Function'),
		'date_start' : fields.date('Start Date', required=True),
		'date_end' : fields.date('End Date'),
		'working_hours_per_day' : fields.integer('Working hours per day'),
		'wage_type_id' : fields.many2one('hr.contract.wage.type', 'Wage Type', required=True),
		'wage' : fields.float('Wage', required=True),
		'notes' : fields.text('Notes'),
	}
	_defaults = {
		'date_start' : lambda *a : DateTime.now().strftime("%Y-%m-%d"),
		'working_hours_per_day' : lambda *a : 8,
	}
hr_contract()

