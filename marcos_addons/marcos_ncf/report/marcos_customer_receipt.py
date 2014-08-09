# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Jean Ventura(<http://venturasystems.net>).
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

from openerp.report import report_sxw
import time


class marcos_customer_receipt(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(marcos_customer_receipt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_lines': self.get_lines,
            'get_balance': self.get_balance
            })

    def get_lines(self, voucher):
        """
        Only get lines that have been paid.

        """

        lines = []
        for line in voucher.line_cr_ids:
            if line.amount > 0:
                lines.append(line)
        return lines

    def get_balance(self, voucher):
        """
        Gets the balance for all customer invoices,
        including the ones not in the current invoice.

        """

        balance = 0
        for line in voucher.line_cr_ids:
            balance = balance + (line.amount_unreconciled - line.amount)
        return balance


report_sxw.report_sxw('report.marcos.customer.receipt','account.voucher','marcos_addons/marcos_ncf/report/marcos_customer_receipt.rml',parser=marcos_customer_receipt)
