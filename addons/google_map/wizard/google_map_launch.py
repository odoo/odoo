# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
from osv import osv
import pooler
from osv import fields
import time

def _launch_wizard(self, cr, uid, data, context):
    address_obj= pooler.get_pool(cr.dbname).get('res.partner.address')
    m= address_obj.browse(cr,uid,data['id'],context)
    url=''
    url="http://maps.google.com/maps?oi=map&q="
    if m.street:
        url+=m.street.replace(' ','+')
    if m.street2:
        url+='+'+m.street2.replace(' ','+')
    if m.city:
        url+='+'+m.city.replace(' ','+')
    if m.state_id:
        url+='+'+m.state_id.name.replace(' ','+')
    if m.country_id:
        url+='+'+m.country_id.name.replace(' ','+')
    if m.zip:
        url+='+'+m.zip.replace(' ','+')
    return {
    'type': 'ir.actions.act_url',
    'url':url,
    'target': 'new'
    }

class launch_map(wizard.interface):

    states= {'init' : {'actions': [],
                       'result':{'type':'action',
                                 'action': _launch_wizard,
                                 'state':'end'}
                       }
             }
launch_map('google_map_launch')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

