# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import logging
import calendar
from datetime import date, datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp.tools.safe_eval import safe_eval as eval
_logger = logging.getLogger(__name__)
# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}


class hr_ke_epay_line(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.epay.line"
        _description = "epayment lines"
	
	name = fields.Char('Name', related='slip_id.name', store=True)
	slip_id = fields.Many2one('hr.payslip')
	slip_no = fields.Char('Ref', related='slip_id.number', store=True)
	employee_name = fields.Char('Employee', related='slip_id.employee_id.name', store=True)
	employee_no = fields.Char('Emp. No', related='slip_id.employee_id.employee_no', store=True)
	pin_no = fields.Char('PIN', related='slip_id.employee_id.tax_pin', store=True)
	id_no = fields.Char('ID No', related='slip_id.employee_id.identification_id', store=True)
	bank_id  = fields.Char('Bank', related='slip_id.employee_id.bank_account_id.bank_name', store=True)
	bank_branch  = fields.Char('Branch', related='slip_id.employee_id.bank_account_id.bank_bic', store=True)
	bank_acc  = fields.Char('Account No', related='slip_id.employee_id.bank_account_id.acc_number', store=True)
	net_pay = fields.Float('Net Pay', digits=(32,2), compute='_compute_net_pay')
	epay_id = fields.Many2one('ke.epay', 'Register')

	@api.one
	def _compute_net_pay(self):
	    self.net_pay = self.slip_id.line_ids.search([('code', '=', 'NET_PAY'), ('slip_id', '=', self.slip_id.id)])[0].total


class hr_ke_epay(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.epay"
        _description = "Electronic Payment Report"


	@api.model
    	def _default_journal(self):
        	inv_type = self._context.get('type', 'out_invoice')
        	inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        	company_id = self._context.get('company_id', self.env.user.company_id.id)
        	domain = [
            		('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            		('company_id', '=', company_id),
        	]
        	return self.env['account.journal'].search(domain, limit=1)

    	@api.model
    	def _default_currency(self):
            journal = self._default_journal()
            return journal.currency or journal.company_id.currency_id

        name = fields.Char('Name', required=True, readonly=True, states={'draft':[('readonly',False)]})
        date_from = fields.Date('Date From', default=date.today().replace(day=1), required=True, readonly=True, 
			states={'draft':[('readonly',False)]})
        date_to = fields.Date('Date To', default=date.today(), required=True, readonly=True, states={'draft':[('readonly',False)]})
	slip_ids = fields.One2many('ke.epay.line', 'epay_id', readonly=True)
	state = fields.Selection([('draft', 'Draft'), ('done','Done')],'Status', default='draft')
	total = fields.Float('Total', digits=(32,2))
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]},
        		default=_default_currency, track_visibility='always')
	@api.multi
	def compute_register(self):
	    for record in self:
	        record.slip_ids.unlink()
	        slips = record.env['hr.payslip'].search([('date_from', '>=', record.date_from), ('date_to', '<=', record.date_to), 
					('state', '=', 'done')])
		total =0.00
		for slip in slips:
		    eslip = record.slip_ids.create({'slip_id': slip.id, 'epay_id': record.id})
	    	    total += eslip.net_pay
		record.write({'total': total})


