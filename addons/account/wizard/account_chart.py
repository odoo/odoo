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

class account_chart(osv.osv_memory):
    """
    For Chart of Accounrs
        """
    _name = "account.chart"
    _description = "chart"
    _columns = {
       'fiscalyear': fields.many2one('account.fiscalyear', \
                                'Fiscal year',  \
                                help = 'Keep empty for all open fiscal years'),
       'target_move': fields.selection([
                                            ('all', 'All Entries'),
                                            ('posted', 'All Posted Entries'),
                                     ], 'Target Moves', required = True),

              }
    def _get_defaults(self, cr, uid, context={}):
            """Return default Fiscalyear value"""
            fiscalyear_obj = self.pool.get('account.fiscalyear')
            fiscalyear = fiscalyear_obj.find(cr, uid)
            return fiscalyear

    def account_chart_open_window(self, cr, uid, ids, context={}):
            """
            Opens chart of Accounts
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of account chart’s IDs
            @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
            """
            mod_obj = self.pool.get('ir.model.data')
            act_obj = self.pool.get('ir.actions.act_window')
            for data in  self.read(cr, uid, ids,context=context):
                result = mod_obj._get_id(cr, uid, 'account', 'action_account_tree')
                id = mod_obj.read(cr, uid, [result], ['res_id'],context=context)[0]['res_id']
                result = act_obj.read(cr, uid, [id], context=context)[0]
                result['context'] = str({'fiscalyear': data['fiscalyear'], \
                                            'state': data['target_move']})
                if data['fiscalyear']:
                    result['name'] += ':' + self.pool.get('account.fiscalyear').read(cr, uid, [data['fiscalyear']],context=context)[0]['code']
                return result


    _defaults = {
        'fiscalyear': _get_defaults,
        'target_move': lambda * a: 'all'
                }
account_chart()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
