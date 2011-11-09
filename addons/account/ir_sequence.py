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

class ir_sequence_fiscalyear(osv.osv):
    _name = 'account.sequence.fiscalyear'
    _rec_name = "sequence_main_id"
    _columns = {
        "sequence_id": fields.many2one("ir.sequence", 'Sequence', required=True,
            ondelete='cascade'),
        "sequence_main_id": fields.many2one("ir.sequence", 'Main Sequence',
            required=True, ondelete='cascade'),
        "fiscalyear_id": fields.many2one('account.fiscalyear', 'Fiscal Year',
            required=True, ondelete='cascade')
    }

    _sql_constraints = [
        ('main_id', 'CHECK (sequence_main_id != sequence_id)',
            'Main Sequence must be different from current !'),
    ]

ir_sequence_fiscalyear()

class ir_sequence(osv.osv):
    _inherit = 'ir.sequence'
    _columns = {
        'fiscal_ids': fields.one2many('account.sequence.fiscalyear',
            'sequence_main_id', 'Sequences')
    }

    def _next(self, cr, uid, seq_ids, context=None):
        for seq in self.browse(cr, uid, seq_ids, context):
            for line in seq.fiscal_ids:
                if line.fiscalyear_id.id == context.get('fiscalyear_id'):
                    return super(ir_sequence, self)._next(cr, uid, [line.sequence_id.id], context)
        return super(ir_sequence, self)._next(cr, uid, seq_ids, context)

ir_sequence()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
