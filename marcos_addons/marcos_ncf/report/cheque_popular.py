# -*- encoding: utf-8 -*-
from openerp.report import report_sxw
import time
from datetime import datetime


class cheque_popular(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(cheque_popular, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'format_check_date': self.format_check_date
            })

    def format_check_date(self, date, idx):
        """
        Format date to fit in pre-printed boxes.

        """

        date_obj = datetime.strptime(date,'%Y-%m-%d')
        return date_obj.strftime('%d%m%Y')[idx]


report_sxw.report_sxw('report.cheque.popular','account.voucher','marcos_addons/marcos_ncf/report/cheque_popular.rml',parser=cheque_popular)
