# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: make_invoice.py 1070 2005-07-29 12:41:24Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import pooler

from osv import fields, osv

def _list_partners(self, cr, uid, data, context):
        list_partner = []
        pool_obj=pooler.get_pool(cr.dbname)
        obj_reg=pool_obj.get('event.registration')
        reg_ids = obj_reg.search(cr, uid, [('event_id','in',data['ids'])])
        data_reg = obj_reg.browse(cr, uid, reg_ids)
        for reg in data_reg:
            if not reg.partner_id.id in list_partner:
                list_partner.append(reg.partner_id.id)
        data['partner_ids'] = list_partner
        return {}

class event_partners(wizard.interface):
    def _reg_partners(self, cr, uid, data, context):
        pool_obj = pooler.get_pool(cr.dbname)
        model_data_ids = pool_obj.get('ir.model.data').search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_partner_form')])
        resource_id = pool_obj.get('ir.model.data').read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
            'domain': "[('id','in', ["+','.join(map(str,data['partner_ids']))+"])]",
            'name': 'Partners',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'views': [(False,'tree'),(resource_id,'form')],
            'type': 'ir.actions.act_window'
        }
        return {}

    states = {
        'init' : {
               'actions' : [_list_partners],
               'result': {'type': 'action' , 'action':_reg_partners, 'state':'end'}
            },

    }

event_partners("event.event_reg_partners")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

