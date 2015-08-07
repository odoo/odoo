import time
from datetime import datetime
from dateutil import relativedelta
from openerp.osv import osv
from openerp import models, fields, api, _
from openerp.report import report_sxw
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError

class hr_ke_report_muster_roll(models.AbstractModel):
    _name = 'report.hr_ke.report_muster_roll'
    @api.multi
    def render_html(self, data=None):
	 #raise ValidationError('Here!!')
         report_obj = self.env['report']
         report = report_obj._get_report_from_name('hr_ke.report_muster_roll')
	 docs = self.env[report.model].browse(self._ids)
	 #raise ValidationError(docs.date_from)
	 res  = []
	 totals  = {}
	 total_basic, total_gross, total_nhif, total_nssf, total_paye, total_net = 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
         for slip in self.env['hr.payslip'].search([('state', '=', 'done'), ('date_from', '>=', docs.date_from), ('date_to', '<=', docs.date_to)], order='employee_id, number'):
		basic = slip.line_ids.search([('code', '=', 'BASIC_SAL'), ('slip_id', '=', slip.id)])[0].total
		gross = slip.line_ids.search([('code', '=', 'GROSS_PAY'), ('slip_id', '=', slip.id)])[0].total
		nhif = slip.line_ids.search([('code', '=', 'NHIF'), ('slip_id', '=', slip.id)])[0].total
		nssf = slip.line_ids.search([('code', '=', 'NSSF'), ('slip_id', '=', slip.id)])[0].total
		paye = slip.line_ids.search([('code', '=', 'NET_TAX'), ('slip_id', '=', slip.id)])[0].total
		net = slip.line_ids.search([('code', '=', 'NET_PAY'), ('slip_id', '=', slip.id)])[0].total
		total_basic += basic; total_gross += gross; total_nhif += nhif;	total_nssf += nssf; total_paye += paye;	total_net += net 
                res.append({
                    'number': slip.employee_id.employee_no, 'employee': slip.employee_id.name, 'basic': basic, 'slip': slip.number, 
		    'gross': gross, 'nhif': nhif, 'nssf': nssf, 'paye': paye, 'net': net,
                })

         totals = { 'tbasic': total_basic, 'tgross': total_gross, 'tnhif': total_nhif, 'tnssf': total_nssf, 'tpaye': total_paye, 'tnet': total_net }

         docargs = {
             'doc_ids': self._ids,
             'doc_model': report.model,
	     'docs': docs,
	     'slips': res,
	     'totals': totals,
         }
	 #raise ValidationError(docs)
         return report_obj.render('hr_ke.report_muster_roll', docargs)
