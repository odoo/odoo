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
import wizard
import osv
import pooler

section_form = '''<?xml version="1.0"?>
<form string="Create Menu">
    <separator string="Menu Information" colspan="4"/>
    <label string="Want to create a Index on Selected Pages ? "/>
</form>'''

def wiki_do_index(self, cr, uid, data, context):
    ids = data['ids']
    pool = pooler.get_pool(cr.dbname)
    wiki_pool = pool.get('wiki.wiki')

    sSQL = "Select id, section from wiki_wiki where id in %s order by section "
    cr.execute(sSQL, (tuple(ids),))
    lst0 = cr.fetchall()
    lst = []
    ids = {}
    for l in lst0:
        ids[l[1]] = l[0]
        lst.append(l[1])

    lst.sort()
    val = None
    def toint(x):
        try:
            return int(x)
        except:
            return 1
    
    lst = map(lambda x: map(toint, x.split('.')), lst)
    
    result = []
    current = ['0']
    current2 = []

    for l in lst:
        for pos in range(len(l)):
            if pos >= len(current):
                current.append('1')
                continue
            if (pos == len(l) - 1) or (pos >= len(current2)) or (toint(l[pos]) > toint(current2[pos])):
                 current[pos] = str(toint(current[pos]) + 1)
                 current = current[:pos + 1]
            if pos == len(l) - 1:
                 break
             
        key = ('.'.join([str(x) for x in l]))
        id = ids[key]
        val = ('.'.join([str(x) for x in current[:]]), id)

        if val:
            result.append(val)
        current2 = l
    
    for rs in result:
        wiki_pool.write(cr, uid, [rs[1]], {'section':rs[0]})
        
    return {}

class make_index(wizard.interface):
    states = {
        'init': {
            'actions': [], 
            'result': {'type':'form', 'arch':section_form, 'fields':{}, 'state':[('end','Cancel'),('yes','Create Index')]}
        },
        'yes': {
            'actions': [wiki_do_index], 
            'result': {
                'type':'state', 
                'state':'end'
            }
        }
    }
make_index('wiki.make.index')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
