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
from osv import fields, osv
from tools.translate import _

class account_reporting_balance_report(osv.osv_memory):

    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalyear = fiscalyear_obj.find(cr, uid)
        return fiscalyear

    _name = 'account.reporting.balance.report'
    _description = 'Account balance report'
    _columns = {
        'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal year', required=True),
        'periods': fields.many2many('account.period', 'acc_reporting_relation', 'acc_id','period_id', 'Periods', help='All periods if empty'),
            }
    _defaults = {
        'fiscalyear' : _get_fiscalyear,
        }

    def check_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.report.bs',
             'form': data
            }
        datas['form']['report_type'] = 'only_obj'
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.report.bs',
            'datas': datas,
            }

account_reporting_balance_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

