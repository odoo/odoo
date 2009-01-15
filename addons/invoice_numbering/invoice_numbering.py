##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
import tools
from osv import fields, osv

import mx.DateTime
import base64


class fiscalyear_seq(osv.osv):
    _name = "fiscalyear.seq"
    _description = "Maintains Invoice sequences with Fiscal Year"
    _rec_name = 'fiscalyear_id'
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year',required=True),
        'sequence_id':fields.many2one('ir.sequence', 'Sequence',required=True),
    }
    
fiscalyear_seq()

class account_journal(osv.osv):
    _inherit = 'account.journal'
    
    _columns = {
        'fy_seq_id': fields.one2many('fiscalyear.seq', 'journal_id', 'Sequences'),
    }
    
account_journal()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def action_number(self, cr, uid, ids, *args):
        cr.execute('SELECT id, type, number, move_id, reference ' \
                'FROM account_invoice ' \
                'WHERE id IN ('+','.join(map(str,ids))+')')
        
        obj_inv = self.browse(cr, uid, ids)[0]
        
        for (id, invtype, number, move_id, reference) in cr.fetchall():
            if not number:
                flag = True
                for seq in obj_inv.journal_id.fy_seq_id:
                    if seq.fiscalyear_id.id == obj_inv.move_id.period_id.fiscalyear_id.id:
                        number =  self.pool.get('ir.sequence').get_id(cr, uid,seq.sequence_id.id)
                        flag = False
                        break
                
                if flag:
                    number = self.pool.get('ir.sequence').get(cr, uid,
                        'account.invoice.' + invtype)
                if type in ('in_invoice', 'in_refund'):
                    ref = reference
                else:
                    ref = self._convert_ref(cr, uid, number)
                cr.execute('UPDATE account_invoice SET number=%s ' \
                        'WHERE id=%d', (number, id))
                cr.execute('UPDATE account_move_line SET ref=%s ' \
                        'WHERE move_id=%d AND (ref is null OR ref = \'\')',
                        (ref, move_id))
                cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                        'FROM account_move_line ' \
                        'WHERE account_move_line.move_id = %d ' \
                            'AND account_analytic_line.move_id = account_move_line.id',
                            (ref, move_id))
        return True
account_invoice()    


