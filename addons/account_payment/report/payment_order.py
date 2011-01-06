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
import datetime
import pooler
from report import report_sxw

class payment_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(payment_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'get_invoice_name': self._get_invoice_name,
            'get_company_currency' : self._get_company_currency,
            'get_amount_total_in_currency' : self._get_amount_total_in_currency,
            'get_amount_total' : self._get_amount_total,
        })
        
    def _get_invoice_name(self,invoice_id):
        if invoice_id:
            pool = pooler.get_pool(self.cr.dbname)
            value_name = pool.get('account.invoice').name_get(self.cr, self.uid, [invoice_id])
            if value_name:
                return value_name[0][1]
        return False
    
    def _get_amount_total_in_currency(self,payment):
        total = 0.0
        if payment.line_ids:
            currency_cmp = payment.line_ids[0].currency.id
        else:
            return False
        for line in payment.line_ids:
            if currency_cmp == line.currency.id:
                total += line.amount_currency
            else:
                return False
        return total

    def _get_amount_total(self,payment):
        total = 0.0
        if not payment.line_ids:
            return False
        for line in payment.line_ids:
            total += line.amount
        return total

            
    def _get_company_currency(self):
        pool = pooler.get_pool(self.cr.dbname)
        user = pool.get('res.users').browse(self.cr, self.uid, self.uid)
        return user.company_id and user.company_id.currency_id and user.company_id.currency_id.name or False 

report_sxw.report_sxw('report.payment.order', 'payment.order', 'addons/account_payment/report/payment_order.rml', parser=payment_order,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
