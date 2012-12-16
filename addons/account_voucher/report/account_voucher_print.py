# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
from tools import amount_to_text_en

class report_voucher_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_voucher_print, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_title': self.get_title,
            'get_lines':self.get_lines,
            'get_on_account':self.get_on_account,
            'convert':self.convert
        })

    def convert(self, amount, cur):
        amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
        return amt_en

    def get_lines(self, voucher):
        result = []
        if voucher.type in ('payment','receipt'):
            type = voucher.line_ids and voucher.line_ids[0].type or False
            for move in voucher.move_ids:
                res = {}
                amount = move.credit
                if type == 'dr':
                    amount = move.debit
                if amount > 0.0:
                    res['pname'] = move.partner_id.name
                    res['ref'] = 'Agst Ref'+" "+str(move.name)
                    res['aname'] = move.account_id.name
                    res['amount'] = amount
                    result.append(res)
        else:
            type = voucher.line_ids and voucher.line_ids[0].type or False
            for move in voucher.move_ids:
                res = {}
                amount = move.credit
                if type == 'dr':
                    amount = move.debit
                if amount > 0.0:
                    res['pname'] = move.partner_id.name
                    res['ref'] =  move.name
                    res['aname'] = move.account_id.name
                    res['amount'] = amount
                    result.append(res)
        return result

    def get_title(self, type):
        title = ''
        if type:
            title = type[0].swapcase() + type[1:] + " Voucher"
        return title

    def get_on_account(self, voucher):
        name = ""
        if voucher.type == 'receipt':
            name = "Received cash from "+str(voucher.partner_id.name)
        elif voucher.type == 'payment':
            name = "Payment from "+str(voucher.partner_id.name)
        elif voucher.type == 'sale':
            name = "Sale to "+str(voucher.partner_id.name)
        elif voucher.type == 'purchase':
            name = "Purchase from "+str(voucher.partner_id.name)
        return name

report_sxw.report_sxw(
    'report.voucher.print',
    'account.voucher',
    'addons/account_voucher/report/account_voucher_print.rml',
    parser=report_voucher_print,header="external"
)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
