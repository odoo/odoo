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

from osv import osv, fields

class account_move(osv.osv):
    _inherit = 'account.move'

    _columns = {
        'internal_sequence_number': fields.char('Internal Sequence Number', size=64, readonly=True),
    }

    def post(self, cr, uid, ids, context=None):
        if context is None: context = {}
        obj_sequence = self.pool.get('ir.sequence')
        res = super(account_move, self).post(cr, uid, ids, context=context)
        seq_no = False
        for line in self.browse(cr, uid, ids, context=context):
            # Todo: if there is not internal seq defined on journal raise error ?
            if line.journal_id.internal_sequence:
                seq_no = obj_sequence.get_id(cr, uid, line.journal_id.internal_sequence.id, context=context)
            if seq_no:
                self.write(cr, uid, [line.id], {'internal_sequence_number': seq_no})
        return res

account_move()

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'internal_sequence': fields.many2one('ir.sequence', 'Internal Sequence'),
    }

account_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: