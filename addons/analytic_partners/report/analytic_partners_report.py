import pooler
import time
from report import report_sxw

class analytic_partners_report(report_sxw.rml_parse):
	# o must be an instance of
	# analytic_partners_account_analytic_account.
	def _init_dict(self, o):
		self.partners_by_account.clear()
 		for a in o.address_ids:
			p = a.partner_id
 			for c in p.category_id:
 				self.partners_by_account.setdefault(c.name, []).append(a)
 			if not p.category_id:
 				self.partners_by_account.setdefault('Non classifie', []).append(a)


	def __init__(self, cr, uid, name, context):
		# self.partners_by_account is a dictionnary where keys are category
		# names and values are lists of partner_id.
		self.partners_by_account={}
		super(analytic_partners_report, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time' : time,
			'_init_dict' : self._init_dict,
			'partners_by_account' : self.partners_by_account,
		} )

report_sxw.report_sxw(
	'report.analytic_partners.print',
	'account.analytic.account',
	'addons/analytic_partners/report/analytic_account_partners.rml',
	parser=analytic_partners_report)
