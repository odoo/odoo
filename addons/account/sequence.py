# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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


from osv import fields, osv

class ir_sequence_fiscalyear(osv.osv):
    _name = 'account.sequence.fiscalyear'
    _rec_name = "sequence_main_id"
    _columns = {
        "sequence_id": fields.many2one("ir.sequence", 'Sequence', required=True, ondelete='cascade'),
        "sequence_main_id": fields.many2one("ir.sequence", 'Main Sequence', required=True, ondelete='cascade'),
        "fiscalyear_id": fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, ondelete='cascade')
    }

    _sql_constraints = [
        ('main_id', 'CHECK (sequence_main_id != sequence_id)',  'Main Sequence must be different from current !'),
    ]

ir_sequence_fiscalyear()

class ir_sequence(osv.osv):
    _inherit = 'ir.sequence'
    _columns = {
        'fiscal_ids' : fields.one2many('account.sequence.fiscalyear', 'sequence_main_id', 'Sequences')
    }

    def get_id(self, cr, uid, sequence_id, test='id=%s', context=None):

        if context is None:
            context = {}
        if test not in ('id=%s', 'code=%s'):
            raise ValueError('invalid test')
        cr.execute('select id from ir_sequence where '+test+' and active=%s', (sequence_id, True,))
        res = cr.dictfetchone()
        if res:
            for line in self.browse(cr, uid, res['id'], context=context).fiscal_ids:
                if line.fiscalyear_id.id==context.get('fiscalyear_id', False):
                    return super(ir_sequence, self).get_id(cr, uid, line.sequence_id.id, test="id=%s", context=context)
        return super(ir_sequence, self).get_id(cr, uid, sequence_id, test, context)
ir_sequence()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
