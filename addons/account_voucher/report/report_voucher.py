# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
from tools import amount_to_text_en


class report_voucher(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_voucher, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'convert':self.convert,
            'debit':self.debit,
            'credit':self.credit,
            'get_ref' : self._get_ref
        })

    def convert(self,amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount,'en',cur);
        return amt_en
    
    def debit(self, move_ids):
        debit = 0.0
        for move in move_ids:#self.pool.get('account.move.line').browse(self.cr, self.uid, move_ids):
            debit +=move.debit
        return debit
    
    def credit(self, move_ids):
        credit = 0.0
        for move in move_ids:#self.pool.get('account.move.line').browse(self.cr, self.uid, move_ids):
            credit +=move.credit
        return credit
    
    def _get_ref(self, voucher_id, move_ids):
        voucher_line = self.pool.get('account.voucher.line').search(self.cr, self.uid, [('partner_id','=',move_ids.partner_id.id), ('voucher_id','=',voucher_id)])
        if voucher_line:
            voucher = self.pool.get('account.voucher.line').browse(self.cr, self.uid, voucher_line)[0]
            return voucher.ref
        else:
            return
report_sxw.report_sxw(
    'report.voucher.cash_receipt',
    'account.voucher',
    'addons/account_voucher/report/report_voucher.rml',
    parser=report_voucher,header=False
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
