# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import logging
from datetime import date, datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp.tools.safe_eval import safe_eval as eval
_logger = logging.getLogger(__name__)

class hr_ke_department(models.Model):
	_inherit = ["hr.department"]
	overtime = fields.Float('Overtime Hourly rate',digits=(32,2), required=True, default=0.00)

class hr_ke_overtime(models.Model):
        _name = "ke.overtime"
        _description = "Overtime Request"
        _inherit = ["mail.thread"]
        _order = "id desc"
        _track = {
          'state': {
            'hr_ke.ke_ovetime_approval': lambda self, cr, uid, obj, ctx=None: obj.state == 'approval',
            'hr_ke.ke_ovetime_approved': lambda self, cr, uid, obj, ctx=None: obj.state == 'approved',
            'hr_ke.ke_ovetime_disapproved': lambda self, cr, uid, obj, ctx=None: obj.state == 'disapproved',
            'hr_ke.ke_ovetime_draft': lambda self, cr, uid, obj, ctx=None: obj.state == 'draft',
            },
	}

        @api.one
        @api.depends('date_from', 'date_to' )
        def compute_hours(self):
         diff = datetime.strptime(self.date_to, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(self.date_from, DEFAULT_SERVER_DATETIME_FORMAT)
         self.hours = (diff.days * 24) + (diff.seconds / 3600)
         if self.hours < 0:
            raise ValidationError("'End Date' is older than 'Start Date' in time entry. Please correct this")

	def default_date(self):
         return datetime.now()
	
	@api.multi
	def _employee_get(self):
		return self.employee_id.search([('user_id', '=', self.env.user.id)]).id

	@api.multi
	def check_login_user(self):
	    for record in self:
	        if record.env.user.id == record.user_id.id: record.same_user = True
	        else: record.same_user = False

	@api.multi
	def check_user_dept(self):
	    for record in self:
	        if record.employee_id.search([('user_id', '=', record.env.user.id)]).department_id.id == record.dept_id.id: record.same_dept = True
		else: record.same_dept = False

	name = fields.Char('Brief Title', required=True, readonly=True, states={'draft':[('readonly',False)]})
	dept_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id')
	employee_id = fields.Many2one('hr.employee', 'Employee Name', default=_employee_get, required=True, domain="[('user_id','=', uid)]",readonly=True, states={'draft':[('readonly',False)]})
	user_id = fields.Many2one('res.users', related='employee_id.user_id')
	state = fields.Selection([('draft', 'Draft'),('approval', 'Waiting Approval'), ('approved', 'Approved'), ('disapproved', 'Dis-approved')],'Status', default='draft')
	date_from = fields.Datetime('Date From', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=default_date)
	date_to = fields.Datetime('Date To', required=True, readonly=True, states={'draft':[('readonly',False)]}, default=default_date)
	hours = fields.Float('Hours', compute='compute_hours', store=True)
	description = fields.Text('Work Details', required=True, readonly=True, states={'draft':[('readonly',False)]})
	contract_id = fields.Many2one('hr.contract', 'Contract', required=True, domain="[('employee_id','=', employee_id)]",readonly=True, states={'draft':[('readonly',False)]})
	same_user = fields.Boolean(compute='check_login_user')
	same_dept = fields.Boolean(compute='check_user_dept')
	@api.multi
	def overtime_approval(self):
     	    for record in self:
		if not record.employee_id:
		   raise ValidationError('Missing Employee record')
		elif not record.employee_id.parent_id:
                  raise ValidationError('Your manager is not added in your HR records, no one to approve your Overtime request.Please consult HR')
		elif not record.employee_id.parent_id.user_id:
		  raise ValidationError('Your manager does have access to the HR system to approve your overtime request. Please consult HR')
		else:
		   record.message_subscribe_users(user_ids=[record.employee_id.parent_id.user_id.id])
		   return record.write({'state': 'approval'})
	
        @api.multi
        def overtime_approved(self):
            for record in self:
		earning_type = self.env['ke.earnings.type'].search([('code', '=', 'OVERTIME')])
		if not earning_type:
		   raise ValidationError('No earning of type OVERTIME defined in the HR system!')
		values = {
		  'contract_id': record.contract_id.id,
		  'computation': 'fixed',
		  'earning_id': earning_type[0].id,
		  'fixed': record.hours * record.dept_id.overtime
		}
		if values:
		   self.env['ke.earnings'].create(values)
		else: raise ValidationError('Missing Overtime details. Please consult HR')
                record.write({'state': 'approved'})

        @api.multi
        def overtime_disapproved(self):
            for record in self:
                record.write({'state': 'disapproved'})

        @api.multi
        def overtime_reset(self):
            for record in self:
		record.create_workflow()
                record.write({'state': 'draft'})

