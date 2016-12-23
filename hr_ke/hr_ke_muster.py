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

class hr_ke_muster(models.Model):
	_inherit = ["mail.thread"]
	_name = "ke.muster"
	_description = "Muster Roll"
	
	
	name = fields.Char('Name', required=True)
	date_from = fields.Date('Date From', default=datetime.now(), required=True)
	date_to = fields.Date('Date To', default=datetime.now(), required=True)
	
#	year = fields.Selection([(num, str(num)) for num in range(1900, (datetime.now().year)+11 )], 'Year', required=True, default=datetime.now().year)
#	month = fields.Selection([(num, calendar.month_name[num]) for num in range(1,13)], 'Month', required=True, default=datetime.now().month)
	

	@api.multi
	def get_payslip(self, month, year):
	    for record in self:
		payslips = record.env['hr.payslip'].search([('date_from:month', '=', month), ('date_from:year', '=', year)])
	    return payslips
