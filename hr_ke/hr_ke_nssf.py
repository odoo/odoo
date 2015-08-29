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


class hr_ke_nssf_line(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.nssf.line"
        _description = "NSSF Contribution"
	
	name = fields.Char('Name', related='slip_id.name', store=True)
	slip_id = fields.Many2one('hr.payslip')
	slip_no = fields.Char('Ref', related='slip_id.number', store=True)
	employee_name = fields.Char('Employee', related='slip_id.employee_id.name', store=True)
	employee_no = fields.Char('Emp. No', related='slip_id.employee_id.employee_no', store=True)
	nssf_no = fields.Char('NSSF No', related='slip_id.employee_id.nssf', store=True)
	id_no = fields.Char('ID No', related='slip_id.employee_id.identification_id', store=True)
	amount = fields.Float('Contribution', digits=(32,2), compute='_compute_nssf')
	nssf_id = fields.Many2one('ke.nssf', 'NSSF Register')

	@api.one
	def _compute_nssf(self):
	    self.amount  = self.slip_id.line_ids.search([('code', '=', 'NSSF'), ('slip_id', '=', self.slip_id.id)])[0].total


class hr_ke_nssf(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.nssf"
        _description = "NSSF Contribution Report"


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
	slip_ids = fields.One2many('ke.nssf.line', 'nssf_id', readonly=True)
	state = fields.Selection([('draft', 'Draft'), ('done','Done')],'Status', default='draft')
	total = fields.Float('Total', digits=(32,2))
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]},
        		default=_default_currency, track_visibility='always')
	@api.multi
	def compute_nssf(self):
	    for record in self:
	        record.slip_ids.unlink()
	        slips = record.env['hr.payslip'].search([('date_from', '>=', record.date_from), ('date_to', '<=', record.date_to), 
					('state', '=', 'done')])
		total =0.00
		for slip in slips:
		    nssfc = record.slip_ids.create({'slip_id': slip.id, 'nssf_id': record.id})
	    	    total += nssfc.amount
		record.write({'total': total})


