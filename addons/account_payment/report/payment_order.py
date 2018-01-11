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
from openerp.osv import osv
from openerp.report import report_sxw


class payment_order(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(payment_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'get_invoice_name': self._get_invoice_name,
            'get_amount_total_in_currency': self._get_amount_total_in_currency,
            'get_amount_total': self._get_amount_total,
            'get_account_name': self._get_account_name,
        })

    def _get_invoice_name(self, invoice_id):
        if invoice_id:
            value_name = self.pool['account.invoice'].name_get(self.cr, self.uid, [invoice_id])
            if value_name:
                return value_name[0][1]
        return False

    def _get_amount_total_in_currency(self, payment):
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

    def _get_amount_total(self, payment):
        total = 0.0
        if not payment.line_ids:
            return False
        for line in payment.line_ids:
            total += line.amount
        return total

    def _get_account_name(self,bank_id):
        if bank_id:
            value_name = self.pool['res.partner.bank'].name_get(self.cr, self.uid, [bank_id])
            if value_name:
                return value_name[0][1]
        return False


class report_paymentorder(osv.AbstractModel):
    _name = 'report.account_payment.report_paymentorder'
    _inherit = 'report.abstract_report'
    _template = 'account_payment.report_paymentorder'
    _wrapped_report_class = payment_order

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
