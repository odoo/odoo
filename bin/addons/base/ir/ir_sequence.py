# -*- coding: utf-8 -*-
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

import time
from osv import fields,osv
import pooler

class ir_sequence_type(osv.osv):
    _name = 'ir.sequence.type'
    _columns = {
        'name': fields.char('Name',size=64, required=True),
        'code': fields.char('Code',size=32, required=True),
    }
ir_sequence_type()

def _code_get(self, cr, uid, context={}):
    cr.execute('select code, name from ir_sequence_type')
    return cr.fetchall()

class ir_sequence(osv.osv):
    _name = 'ir.sequence'
    _columns = {
        'name': fields.char('Name',size=64, required=True),
        'code': fields.selection(_code_get, 'Code',size=64, required=True),
        'active': fields.boolean('Active'),
        'prefix': fields.char('Prefix',size=64, help="Prefix value of the record for the sequence"),
        'suffix': fields.char('Suffix',size=64, help="Suffix value of the record for the sequence"),
        'number_next': fields.integer('Next Number', required=True, help="Next number of this sequence"),
        'number_increment': fields.integer('Increment Number', required=True, help="The next number of the sequence will be incremented by this number"),
        'padding' : fields.integer('Number padding', required=True, help="OpenERP will automatically adds some '0' on the left of the 'Next Number' to get the required padding size."),
        'company_id': fields.many2one('res.company', 'Company'),
    }
    _defaults = {
        'active': lambda *a: True,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'ir.sequence', context=c),
        'number_increment': lambda *a: 1,
        'number_next': lambda *a: 1,
        'padding' : lambda *a : 0,
    }

    def _process(self, s):
        return (s or '') % {
            'year':time.strftime('%Y'),
            'month': time.strftime('%m'),
            'day':time.strftime('%d'),
            'y': time.strftime('%y'),
            'doy': time.strftime('%j'),
            'woy': time.strftime('%W'),
            'weekday': time.strftime('%w'),
            'h24': time.strftime('%H'),
            'h12': time.strftime('%I'),
            'min': time.strftime('%M'),
            'sec': time.strftime('%S'),
        }

    def get_id(self, cr, uid, sequence_id, test='id', context=None):
        assert test in ('code','id')
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        seq_id = self.search(cr, uid, [(test,'=',sequence_id),('active','=',True),('company_id','=',company_id)])
        if not seq_id:
            seq_id = self.search(cr, uid, [(test,'=',sequence_id),('active','=',True),('company_id','=',False)])
        if seq_id:
            sequece_data = self.browse(cr, uid, seq_id[0], context)
            self.write(cr, uid, sequece_data.id, {'number_next': sequece_data.number_next + sequece_data.number_increment})
            if sequece_data.number_next:
                return self._process(sequece_data.prefix) + '%%0%sd' % sequece_data.padding % sequece_data.number_next + self._process(sequece_data.suffix)
            else:
                return self._process(sequece_data.prefix) + self._process(sequece_data.suffix)
        return False

    def get(self, cr, uid, code):
        return self.get_id(cr, uid, code, test='code')
ir_sequence()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
