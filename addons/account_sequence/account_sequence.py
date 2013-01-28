# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class account_move(osv.osv):
    _inherit = 'account.move'

    _columns = {
        'internal_sequence_number': fields.char('Internal Number', size=64, readonly=True, help='Internal Sequence Number'),
    }

    def post(self, cr, uid, ids, context=None):
        obj_sequence = self.pool.get('ir.sequence')
        res = super(account_move, self).post(cr, uid, ids, context=context)
        seq_no = False
        for move in self.browse(cr, uid, ids, context=context):
            if move.journal_id.internal_sequence_id:
                seq_no = obj_sequence.next_by_id(cr, uid, move.journal_id.internal_sequence_id.id, context=context)
            if seq_no:
                self.write(cr, uid, [move.id], {'internal_sequence_number': seq_no})
        return res

account_move()

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'internal_sequence_id': fields.many2one('ir.sequence', 'Internal Sequence', help="This sequence will be used to maintain the internal number for the journal entries related to this journal."),
    }

account_journal()

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns = {
        'internal_sequence_number': fields.related('move_id','internal_sequence_number', type='char', relation='account.move', help='Internal Sequence Number', string='Internal Number'),
    }

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
