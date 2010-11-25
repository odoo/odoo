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

class account_sequence_installer(osv.osv_memory):
    _name = 'account.sequence.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'internal_sequence': fields.many2one('ir.sequence', 'Internal Sequence', help="This sequence will be used on Journals to maintain internal number for accounting entries."),
    }

    def _get_internal_sequence(self, cr, uid, context=None):
        result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_sequence', 'internal_sequence_journal')
        return result and result[1] or False

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        jou_obj = self.pool.get('account.journal')
        obj_sequence = self.pool.get('ir.sequence')
        record = self.browse(cr, uid, ids)[0]
        j_ids = []
        res =  super(account_sequence_installer, self).execute(cr, uid, ids, context=context)
        journal_ids = jou_obj.search(cr, uid, [], context=context)
        for journal in jou_obj.browse(cr, uid, journal_ids):
            if not journal.internal_sequence:
                j_ids.append(journal.id)
        if j_ids:
            jou_obj.write(cr, uid, j_ids, {'internal_sequence': record.internal_sequence.id})
        return res

    _defaults = {
        'internal_sequence': _get_internal_sequence
    }

account_sequence_installer()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: