import pooler
import time
from report import report_sxw

class analytic_partners_report(report_sxw.rml_parse):
	# o must be an instance of analytic_partners_account_analytic_account.
	# contacts_by_partners_by_account returns a list of categories. Each
	# category contains a list of partner names, each partner name contains
	# a list of partner contacts. This list reflects the selected partners
	# contacts for the selected analytic account.
	def contacts_by_partners_by_categories(self, o):
		categs = {} 
		
	def __init__(self, cr, uid, name, context):
		super(analytic_partners_report, self).__init__(cr, uid, name, context)
		self.localcontext.update( {
			'time' : time,
			'contacts_by_partners_by_categories' : self.contacts_by_partners_by_categories,
		} )

report_sxw.report_sxw(
	'report.analytic_partners.print',
	'account.analytic.account',
	'addons/analytic_partners/report/analytic_account_partners.rml',
	parser=analytic_partners_report)
