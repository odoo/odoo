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

class account_sequence_installer(osv.osv_memory):
    _name = 'account.sequence.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'name': fields.char('Name', required=True),
        'prefix': fields.char('Prefix', size=64, help="Prefix value of the record for the sequence"),
        'suffix': fields.char('Suffix', size=64, help="Suffix value of the record for the sequence"),
        'number_next': fields.integer('Next Number', required=True, help="Next number of this sequence"),
        'number_increment': fields.integer('Increment Number', required=True, help="The next number of the sequence will be incremented by this number"),
        'padding' : fields.integer('Number padding', required=True, help="OpenERP will automatically adds some '0' on the left of the 'Next Number' to get the required padding size."),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.sequence', context=c),
        'number_increment': 1,
        'number_next': 1,
        'padding' : 0,
        'name': 'Internal Sequence Journal',
    }

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record = self.browse(cr, uid, ids, context=context)[0]
        j_ids = []
        if record.company_id:
            company_id = record.company_id.id,
            search_criteria = [('company_id', '=', company_id)]
        else:
            company_id = False
            search_criteria = []
        vals = {
            'id': 'internal_sequence_journal',
            'code': 'account.journal',
            'name': record.name,
            'prefix': record.prefix,
            'suffix': record.suffix,
            'number_next': record.number_next,
            'number_increment': record.number_increment,
            'padding' : record.padding,
            'company_id': company_id,
        }

        obj_sequence = self.pool.get('ir.sequence')
        ir_seq = obj_sequence.create(cr, uid, vals, context)
        res =  super(account_sequence_installer, self).execute(cr, uid, ids, context=context)
        jou_obj = self.pool.get('account.journal')
        journal_ids = jou_obj.search(cr, uid, search_criteria, context=context)
        for journal in jou_obj.browse(cr, uid, journal_ids, context=context):
            if not journal.internal_sequence_id:
                j_ids.append(journal.id)
        if j_ids:
            jou_obj.write(cr, uid, j_ids, {'internal_sequence_id': ir_seq})
        ir_values_obj = self.pool.get('ir.values')
        ir_values_obj.set(cr, uid, key='default', key2=False, name='internal_sequence_id', models =[('account.journal', False)], value=ir_seq)
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
