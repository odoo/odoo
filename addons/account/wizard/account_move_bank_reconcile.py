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

class account_move_bank_reconcile(osv.osv_memory):
    """
        Bank Reconciliation
    """
    _name = "account.move.bank.reconcile"
    _description = "Move bank reconcile"
    _columns = {
       'journal_id': fields.many2one('account.journal', 'Journal', required=True),
    }

    def action_open_window(self, cr, uid, ids, context=None):
        """
       @param cr: the current row, from the database cursor,
       @param uid: the current user’s ID for security checks,
       @param ids: account move bank reconcile’s ID or list of IDs
       @return: dictionary of  Open  account move line   on given journal_id.
        """
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        cr.execute('select default_credit_account_id \
                        from account_journal where id=%s', (data['journal_id'],))
        account_id = cr.fetchone()[0]
        if not account_id:
             raise osv.except_osv(_('Error!'), _('You have to define \
the bank account\nin the journal definition for reconciliation.'))
        return {
            'domain': "[('journal_id','=',%d), ('account_id','=',%d), ('state','<>','draft')]" % (data['journal_id'], account_id),
            'name': _('Standard Encoding'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'context': "{'journal_id': %d}" % (data['journal_id'],),
            'type': 'ir.actions.act_window'
             }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
