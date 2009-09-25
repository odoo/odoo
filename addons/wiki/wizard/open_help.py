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


import wizard
import netsvc
import time
import pooler
from osv import osv
from tools.translate import _

class wiz_open_help(wizard.interface):
    
    def _open_wiki_page(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        pages = pool.get('wiki.wiki').search(cr, uid, [('name','=','Basic Wiki Editing')])
        
        value = {
            'name': 'Basic Wiki Editing',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'wiki.wiki',
            'view_id': False,
            'res_id': pages[0],
            'type': 'ir.actions.act_window',
        }
                    
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_wiki_page, 'state':'end'}
        }
    }
wiz_open_help('wiki.wiki.help.open')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

