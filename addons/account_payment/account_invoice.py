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

from datetime import datetime

from osv import fields, osv

class Invoice(osv.osv):
    _inherit = 'account.invoice'

    def _amount_to_pay(self, cursor, user, ids, name, args, context=None):
        '''Return the amount still to pay regarding all the payment orders'''
        if not ids:
            return {}
        res = {}
        for invoice in self.browse(cursor, user, ids, context=context):
            res[invoice.id] = 0.0
            if invoice.move_id:
                for line in invoice.move_id.line_id:
                    if not line.date_maturity or \
                            datetime.strptime(line.date_maturity, '%Y-%m-%d') \
                            < datetime.today():
                        res[invoice.id] += line.amount_to_pay
        return res

    _columns = {
        'amount_to_pay': fields.function(_amount_to_pay,
            type='float', string='Amount to be paid',
            help='The amount which should be paid at the current date\n' \
                    'minus the amount which is already in payment order'),
    }

Invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: