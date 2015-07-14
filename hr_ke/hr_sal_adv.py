# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import logging
from datetime import date, datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp.tools.safe_eval import safe_eval as eval
_logger = logging.getLogger(__name__)


class hr_ke_sal_advance(models.Model):
        _name = "ke.advance"
        _description = "Salary Advance Request"
        _inherit = ["mail.thread"]
        _order = "id desc"
        _track = {
          'state': {
            'hr_ke.ke_advance_approval': lambda self, cr, uid, obj, ctx=None: obj.state == 'approval',
            'hr_ke.ke_advance_approved': lambda self, cr, uid, obj, ctx=None: obj.state == 'approved',
            'hr_ke.ke_advance_disapproved': lambda self, cr, uid, obj, ctx=None: obj.state == 'disapproved',
            'hr_ke.ke_advance_draft': lambda self, cr, uid, obj, ctx=None: obj.state == 'draft',
            },
	}

	
	@api.multi
	def _employee_get(self):
		return self.employee_id.search([('user_id', '=', self.env.user.id)]).id

	@api.multi
	def check_login_user(self):
	    for record in self:
	        if record.env.user.id == record.user_id.id: record.same_user = True
	        else: record.same_user = False


	name = fields.Char('Request details', required=True, readonly=True, states={'draft':[('readonly',False)]})
	dept_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id')
	employee_id = fields.Many2one('hr.employee', 'Employee Name', default=_employee_get, required=True, domain="[('user_id','=', uid)]",readonly=True, states={'draft':[('readonly',False)]})
	user_id = fields.Many2one('res.users', related='employee_id.user_id')
	state = fields.Selection([('draft', 'Draft'),('approval', 'Waiting Approval'), ('approved', 'Approved'), ('disapproved', 'Dis-approved')],'Status', default='draft')
	amount = fields.Float('Amount', digits=(32,2))
	description = fields.Text('Reasons for Request', required=True, readonly=True, states={'draft':[('readonly',False)]})
	contract_id = fields.Many2one('hr.contract', 'Contract', required=True, domain="[('employee_id','=', employee_id)]",readonly=True, states={'draft':[('readonly',False)]})
	same_user = fields.Boolean(compute='check_login_user')

	@api.multi
	def advance_approval(self):
     	    for record in self:
		if not record.employee_id:
		   raise ValidationError('Missing Employee record')
		elif not record.employee_id.parent_id:
                  raise ValidationError('Your manager is not added in your HR records, no one to approve your salary advance request.Please consult HR')
		elif not record.employee_id.parent_id.user_id:
		  raise ValidationError('Your manager does have access to the HR system to approve your salary advance request. Please consult HR')
		else:
		   record.message_subscribe_users(user_ids=[record.employee_id.parent_id.user_id.id])
		   return record.write({'state': 'approval'})
	
        @api.multi
        def advance_approved(self):
            for record in self:
		deduction_type = self.env['ke.deductions.type'].search([('code', '=', 'SAL_ADV')])
		if not deduction_type:
		   raise ValidationError("No Deduction of type 'SALARY ADVANCE' defined in the HR system!")
		values = {
		  'employee_id': record.employee_id.id,
		  'computation': 'fixed',
		  'deduction_id': deduction_type[0].id,
		  'fixed': record.amount
		}
		if values:
		   self.env['ke.deductions'].create(values)
		else: raise ValidationError('Missing Salary Advance details. Please consult HR')
                record.write({'state': 'approved'})

        @api.multi
        def advance_disapproved(self):
            for record in self:
                record.write({'state': 'disapproved'})

        @api.multi
        def advance_reset(self):
            for record in self:
		record.create_workflow()
                record.write({'state': 'draft'})

