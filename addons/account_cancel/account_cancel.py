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
import netsvc
from osv import fields, osv
from tools.translate import _

class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'update_posted': fields.boolean('Allow Cancelling Entries',help="Check this box if you want to cancel the entries related to this journal or want to cancel the invoice related to this journal")
    }

account_journal()

class account_move(osv.osv):
    _inherit = "account.move"
    _description = "Account Entry"
    
    def button_cancel(self, cr, uid, ids, context={}):
        for line in self.browse(cr, uid, ids, context):
            if not line.journal_id.update_posted:
                raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of this journal !\nYou should set the journal to allow cancelling entries if you want to do that.'))
        if len(ids):
            cr.execute('update account_move set state=%s where id =ANY(%s)',('draft',ids,))
        return True

account_move()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    
    def action_cancel(self, cr, uid, ids, *args):
        account_move_obj = self.pool.get('account.move')
        invoices = self.read(cr, uid, ids, ['move_id', 'payment_ids'])
        for i in invoices:
            if i['move_id']:
                account_move_obj.button_cancel(cr, uid, [i['move_id'][0]])
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                account_move_obj.unlink(cr, uid, [i['move_id'][0]])
        return super(account_invoice, self).action_cancel(cr, uid, ids, *args)
    
account_invoice()    