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
	 #sal_obj = self.env['hr.salary.rule']
	 basic_sal_code = self.env.ref('hr_ke.ke_rule1').code
	 basic_wage_code_PD = self.env.ref('hr_ke.ke_rule25').code
	 basic_wage_code_PH = self.env.ref('hr_ke.ke_rule24').code
	 gross_code = self.env.ref('hr_ke.ke_rule2').code
	 nhif_code = self.env.ref('hr_ke.ke_rule21').code
	 nssf_code = self.env.ref('hr_ke.ke_rule20').code
	 net_tax_code = self.env.ref('hr_ke.ke_rule22').code
	 net_pay_code = self.env.ref('hr_ke.ke_rule3').code
	 #gross_id = self.env.ref('hr_ke.ke_rule2')
	 #basic_rule = sal_obj.search([('id', '=', basic_id.id)], limit=1)[0]
	 #gross_rule = sal_obj.browse([gross_id])
	 #k = basic_rule.code
	 #raise ValidationError(k)
	 res  = []
	 totals  = {}
	 total_basic, total_gross, total_nhif, total_nssf, total_paye, total_net = 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
         for slip in self.env['hr.payslip'].search([('state', '=', 'done'), ('date_from', '>=', docs.date_from), ('date_to', '<=', docs.date_to)], order='employee_id, number'):
		
	 	#basic_id = self.env.ref('hr_ke.ke_rule1').code
		#raise ValidationError(slip)
		basic_wage_PD = slip.line_ids.search([('code', '=', basic_wage_code_PD), ('slip_id', '=', slip.id)], limit=1).total
		basic_wage_PH = slip.line_ids.search([('code', '=', basic_wage_code_PH), ('slip_id', '=', slip.id)], limit=1).total
		basic_sal = slip.line_ids.search([('code', '=', basic_sal_code), ('slip_id', '=', slip.id)], limit=1).total
		basic = basic_wage_PD or basic_wage_PH or basic_sal
		gross = slip.line_ids.search([('code', '=', gross_code), ('slip_id', '=', slip.id)], limit=1).total
		nhif = slip.line_ids.search([('code', '=', nhif_code), ('slip_id', '=', slip.id)], limit=1).total
		nssf = slip.line_ids.search([('code', '=', nssf_code), ('slip_id', '=', slip.id)],limit=1).total
		paye = slip.line_ids.search([('code', '=', net_tax_code), ('slip_id', '=', slip.id)], limit=1).total
		net = slip.line_ids.search([('code', '=', net_pay_code), ('slip_id', '=', slip.id)], limit=1).total
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
