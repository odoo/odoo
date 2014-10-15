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

from openerp import models, fields, api

class ir_sequence_fiscalyear(models.Model):
    _name = 'account.sequence.fiscalyear'
    _rec_name = "sequence_main_id"

    sequence_id = fields.Many2one('ir.sequence', string='Sequence', required=True,
        ondelete='cascade')
    sequence_main_id = fields.Many2one('ir.sequence', string='Main Sequence',
        required=True, ondelete='cascade')
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year',
        required=True, ondelete='cascade')

    _sql_constraints = [
        ('main_id', 'CHECK (sequence_main_id != sequence_id)', 'Main Sequence must be different from current !'),
    ]


class ir_sequence(models.Model):
    _inherit = 'ir.sequence'

    fiscal_ids = fields.One2many('account.sequence.fiscalyear', 'sequence_main_id', string='Sequences', copy=True)

    @api.cr_uid_ids_context
    def _next(self, cr, uid, seq_ids, context=None):
        if context is None:
            context = {}
        for seq in self.browse(cr, uid, seq_ids, context):
            for line in seq.fiscal_ids:
                if line.fiscalyear_id.id == context.get('fiscalyear_id'):
                    return super(ir_sequence, self)._next(cr, uid, [line.sequence_id.id], context)
        return super(ir_sequence, self)._next(cr, uid, seq_ids, context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
