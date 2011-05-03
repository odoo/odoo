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

from osv import osv, fields

class account_invoice_special_msg(osv.osv_memory):
    _name = 'account.invoice.special.msg'
    _description = 'Account Invoice Special Message'

    _columns = {
        'message': fields.many2one('notify.message', 'Message', required = True, help="Message to Print at the bottom of report"),
        }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids, [], context=context)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.invoice',
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'notify_account.invoice',
            'datas': datas,
        }

account_invoice_special_msg()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: