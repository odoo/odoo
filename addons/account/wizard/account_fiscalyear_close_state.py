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
from openerp.tools.translate import _

class account_fiscalyear_close_state(osv.osv_memory):
    """
    Closes  Account Fiscalyear
    """
    _name = "account.fiscalyear.close.state"
    _description = "Fiscalyear Close state"
    _columns = {
       'fy_id': fields.many2one('account.fiscalyear', \
                                 'Fiscal Year to Close', required=True, help="Select a fiscal year to close"),
    }

    def data_save(self, cr, uid, ids, context=None):
        """
        This function close account fiscalyear
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Account fiscalyear close state’s IDs

        """
        for data in  self.read(cr, uid, ids, context=context):
            fy_id = data['fy_id'][0]

            cr.execute('UPDATE account_journal_period ' \
                        'SET state = %s ' \
                        'WHERE period_id IN (SELECT id FROM account_period \
                        WHERE fiscalyear_id = %s)',
                    ('done', fy_id))
            cr.execute('UPDATE account_period SET state = %s ' \
                    'WHERE fiscalyear_id = %s', ('done', fy_id))
            cr.execute('UPDATE account_fiscalyear ' \
                    'SET state = %s WHERE id = %s', ('done', fy_id))

            return {'type': 'ir.actions.act_window_close'}

account_fiscalyear_close_state()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
