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


class hr_ke_nhif_line(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.nhif.line"
        _description = "NHIF Contribution"
	
	name = fields.Char('Name', related='slip_id.name', store=True)
	slip_id = fields.Many2one('hr.payslip')
	slip_no = fields.Char('Ref', related='slip_id.number', store=True)
	employee_name = fields.Char('Employee', related='slip_id.employee_id.name', store=True)
	employee_no = fields.Char('Emp. No', related='slip_id.employee_id.employee_no', store=True)
	nhif_no = fields.Char('NHIF No', related='slip_id.employee_id.nhif', store=True)
	id_no = fields.Char('ID No', related='slip_id.employee_id.identification_id', store=True)
	amount = fields.Float('Contribution', digits=(32,2), compute='_compute_nhif')
	nhif_id = fields.Many2one('ke.nhif', 'NHIF Register', required=True, select=True)

	@api.one
	def _compute_nhif(self):
	    self.amount  = self.slip_id.line_ids.search([('code', '=', 'NHIF'), ('slip_id', '=', self.slip_id.id)])[0].total


class hr_ke_nhif(models.Model):
        _inherit = ["mail.thread"]
        _name = "ke.nhif"
        _description = "NHIF Contribution Report"


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
	slip_ids = fields.One2many('ke.nhif.line', 'nhif_id', 'Contributions', readonly=False)
	state = fields.Selection([('draft', 'Draft'), ('done','Done')],'Status', default='draft')
	total = fields.Float('Total', digits=(32,2))
	currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]},
        		default=_default_currency, track_visibility='always')
	@api.multi
	def compute_nhif(self):
	    for record in self:
	        record.slip_ids.unlink()
	        slips = record.env['hr.payslip'].search([('date_from', '>=', record.date_from), ('date_to', '<=', record.date_to), 
					('state', '=', 'done')])
		total =0.00
		for slip in slips:
		    nhifc = record.slip_ids.create({'slip_id': slip.id, 'nhif_id': record.id})
	    	    total += nhifc.amount
		record.write({'total': total})


