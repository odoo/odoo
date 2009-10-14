# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard
import math
from osv import osv
from tools.misc import UpdateableStr
import pooler

def _is_pair(x):
    return not x%2

def _get_ean_key(string):
    if not string or string=='':
        return '0'
    if len(string)!=12:
        return '0'
    sum=0
    for i in range(12):
        if _is_pair(i):
            sum+=int(string[i])
        else:
            sum+=3*int(string[i])
    return str(int(math.ceil(sum/10.0)*10-sum))

#FIXME: this is not concurrency safe !!!!
_check_arch = UpdateableStr()
_check_fields = {}

def _check_key(self, cr, uid, data, context):
    partner_table=pooler.get_pool(cr.dbname).get('res.partner')
    partners = partner_table.browse(cr, uid, data['ids'])
    _check_arch_lst=['<?xml version="1.0"?>', '<form string="Check EAN13">', '<label string=""/>', '<label string=""/>','<label string="Original" />', '<label string="Computed" />']
    for partner in partners:
        if partner['ean13'] and len(partner['ean13'])>11 and len(partner['ean13'])<14:
            _check_arch_lst.append('<label colspan="2" string="%s" />' % partner['ean13']);
            key=_get_ean_key(partner['ean13'][:12])
            _check_arch_lst.append('<label string=""/>')
            if len(partner['ean13'])==12:
                _check_arch_lst.append('<label string="" />');
            else:
                _check_arch_lst.append('<label string="%s" />' % partner['ean13'][12])
            _check_arch_lst.append('<label string="%s" />' % key)
    _check_arch_lst.append('</form>')
    _check_arch.string = '\n'.join(_check_arch_lst)
    return {}

def _update_ean(self, cr, uid, data, context):
    partner_table = pooler.get_pool(cr.dbname).get('res.partner')
    partners = partner_table.browse(cr, uid, data['ids'])
    for partner in partners:
        partner_table.write(cr, uid, data['ids'], {
            'ean13': "%s%s" % (partner['ean13'][:12], _get_ean_key(partner['ean13'][:12]))
        })
    return {}

class wiz_ean_check(wizard.interface):
    states = {
        'init': {
            'actions': [_check_key],
            'result': {
                'type': 'form',
                'arch': _check_arch,
                'fields': _check_fields,
                'state': (('end', 'Ignore'), ('correct', 'Correct EAN13'))
            }
        },
        'correct' : {
            'actions': [_update_ean],
            'result': {
                'type': 'state',
                'state': 'end'
            }
        }
    }

wiz_ean_check('res.partner.ean13')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

