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

from openerp.osv import fields, osv
import time

class audittrail_view_log(osv.osv_memory):

    _name = "audittrail.view.log"
    _description = "View Log"
    _columns = {
              'from':fields.datetime('Log From'),
              'to':fields.datetime('Log To', required = True)
             }
    _defaults = {
             'to': lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
           }

    def log_open_window(self, cr, uid, ids, context=None):
        """
        Open Log  form from given date range..
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of audittrail view log’s IDs.
        @return: Dictionary of  audittrail log form on given date range.
        """

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj._get_id(cr, uid, 'audittrail', 'action_audittrail_log_tree')
        id = mod_obj.read(cr, uid, [result], ['res_id'], context=context)[0]['res_id']
        result = act_obj.read(cr, uid, [id], context=context)[0]

        #start Loop
        for datas in self.read(cr, uid, ids, context=context):
            if not datas.get('from', None):
                if  datas.get('to') <> time.strftime("%Y-%m-%d %H:%M:%S"):
                    result['domain'] = str([('timestamp', '<', datas.get('to'))])
                else:
                    pass
            else:
                result['domain'] = str([('timestamp', '>', datas.get('from', None)), ('timestamp', '<', datas.get('to'))])
        #End Loop
        return result

audittrail_view_log()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
