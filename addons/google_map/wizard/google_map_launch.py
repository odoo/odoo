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

from osv import osv
import pooler
from osv import fields
import time

class launch_map(osv.osv_memory):
    
    _name = "launch.map"

    def launch_wizard(self, cr, uid, data, context=None):
        address_obj= pooler.get_pool(cr.dbname).get('res.partner.address')
        m = address_obj.browse(cr, uid, data, context=context)[0]
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

launch_map()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

