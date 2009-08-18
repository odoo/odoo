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

import time
from osv import fields,osv
import pooler

class ir_sequence_type(osv.osv):
    _name = 'ir.sequence.type'
    _columns = {
        'name': fields.char('Sequence Name',size=64, required=True),
        'code': fields.char('Sequence Code',size=32, required=True),
    }
ir_sequence_type()

def _code_get(self, cr, uid, context={}):
    cr.execute('select code, name from ir_sequence_type')
    return cr.fetchall()

class ir_sequence(osv.osv):
    _name = 'ir.sequence'
    _columns = {
        'name': fields.char('Sequence Name',size=64, required=True),
        'code': fields.selection(_code_get, 'Sequence Code',size=64, required=True),
        'active': fields.boolean('Active'),
        'prefix': fields.char('Prefix',size=64),
        'suffix': fields.char('Suffix',size=64),
        'number_next': fields.integer('Next Number', required=True),
        'number_increment': fields.integer('Increment Number', required=True),
        'padding' : fields.integer('Number padding', required=True),
    }
    _defaults = {
        'active': lambda *a: True,
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

    def get_id(self, cr, uid, sequence_id, test='id=%s', context=None):
        # as we have to commit, we must create a fresh new cursor
        cr = pooler.get_db(cr.dbname).cursor()
        try:
            cr.execute('SELECT id, number_next, prefix, suffix, padding FROM ir_sequence WHERE '+test+' AND active=%s FOR UPDATE', (sequence_id, True))
            res = cr.dictfetchone()
            if res:
                cr.execute('UPDATE ir_sequence SET number_next=number_next+number_increment WHERE id=%s AND active=%s', (res['id'], True))
                if res['number_next']:
                    return self._process(res['prefix']) + '%%0%sd' % res['padding'] % res['number_next'] + self._process(res['suffix'])
                else:
                    return self._process(res['prefix']) + self._process(res['suffix'])
        finally:
            cr.commit()
            cr.close()
        return False

    def get(self, cr, uid, code):
        return self.get_id(cr, uid, code, test='code=%s')
ir_sequence()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

