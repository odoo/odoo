# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    
    iid = ','.join([str(x) for x in ids])
    sSQL = "Select id, section from wiki_wiki where id in (%s) order by section " % (iid)
    cr.execute(sSQL)
    wiki = cr.fetchall()
    i = 1
    for wk in wiki:
        wiki_pool.write(cr, uid, [wk[0]], {'section':i})
        i+=1
        
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

