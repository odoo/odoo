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
import wizard
import netsvc
import pooler

def _wo_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    current_auction=pool.get('auction.dates').browse(cr,uid,data['id'])
    v_lots=pool.get('auction.lots').search(cr,uid,[('auction_id','=',current_auction.id)])
    v_ids=pool.get('auction.lots').browse(cr,uid,v_lots)
    for ab in v_ids:
        if not ab.auction_id :
            raise wizard.except_wizard('Error!','No Lots belong to this Auction Date')
    return 'report'

class wizard_report(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result' : {'type': 'choice', 'next_state': _wo_check }
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'auction.cat_flagy', 'state':'end'}
        }
    }
wizard_report('auction.catalog.flagey')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

