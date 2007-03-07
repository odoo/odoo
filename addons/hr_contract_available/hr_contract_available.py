from osv import fields, osv

class hr_employee(osv.osv):
	_inherit = "hr.employee"
	def _get_state(self, cr, uid, ids, name, args, context):
		result = {}
		for emp in self.browse(cr, uid, ids, context):
			result[emp.id] = 'no'
			for alloc in emp.allocation_ids:
				if ((not alloc.date_end) or (alloc.date_end>='%Y-%m-%d')) and (alloc.date_start<='%Y-%m-%d'):
					result[emp.id] = alloc.state
		return result
	def _get_date_end(self, cr, uid, ids, name, args, context):
		result = {}
		for emp in self.browse(cr, uid, ids, context):
			result[emp.id] = False
			if len( emp.allocation_ids):
				result[emp.id] = emp.allocation_ids[-1].date_end or False
		return result
	def _get_department_id(self, cr, uid, ids, name, args, context):
		result = {}
		for emp in self.browse(cr, uid, ids, context):
			result[emp.id] = time.strftime('%Y-%m-%d')
			for alloc in emp.allocation_ids:
				if ((not alloc.date_end) or (alloc.date_end>='%Y-%m-%d')) and (alloc.date_start<='%Y-%m-%d'):
					result[emp.id] = alloc.department_id.id
		return result
	_columns = {
		'allocation_ids' : fields.one2many('hr.allocation', 'employee_id', 'Allocations'),
		'allocation_state': fields.function(_get_state,
			method=True,
			type='selection',
			selection=[('no','/'),('unavailable','Unavailable'),('ondemand','On demand'),('available','Available')],
			string='Current Availability'),
		'allocation_department_id': fields.function(_get_department_id, method=True, type='many2one', relation='res.company', string='Current Department'),
		'allocation_date_end': fields.function(_get_date_end, method=True, type='date', string='Availability Date')
	}
hr_employee()

class hr_allocation(osv.osv):
	_name = 'hr.allocation'
	_description = 'Allocations'
	_columns = {
		'name' : fields.char('Contract Name', size=30, required=True),
		'employee_id' : fields.many2one('hr.employee', 'Employee', required=True, relate=True),
		'department_id' : fields.many2one('res.company', 'Department', required=True, relate=True),
		'function' : fields.many2one('res.partner.function', 'Function'),
		'date_start' : fields.date('Start Date', required=True),
		'date_end' : fields.date('End Date', help="Keep empty for unlimited allocation."),
		'state' : fields.selection([('unavailable','Unavailable'),('ondemand','On demand'),('available','Available')], 'State', required=True),
	}
	_order = 'date_start'
	_defaults = {
		'date_start' : lambda *a : DateTime.now().strftime("%Y-%m-%d"),
		'state' : lambda *a : 'ondemand',
		'department_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
	}
hr_contract()

