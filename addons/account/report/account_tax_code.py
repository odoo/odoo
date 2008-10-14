import time
import pooler
import rml_parse
import copy
from report import report_sxw
import re

class account_tax_code_report(rml_parse.rml_parse):
    _name = 'report.account.tax.code.entries'
    def __init__(self, cr, uid, name, context):
        super(account_tax_code_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
        })

        
report_sxw.report_sxw('report.account.tax.code.entries', 'account.tax.code',
    'addons/account/report/account_tax_code.rml', parser=account_tax_code_report, header=False)

