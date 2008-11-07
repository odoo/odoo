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

import wizard
import netsvc

class wizard_clear_ids(wizard.interface):
    def _clear_ids(self, cr, uid, data, context):
        service = netsvc.LocalService("object_proxy")
        service.execute(cr.dbname, uid, 'res.partner', 'write', data['ids'], {'ref': False})
        return {}
        
    states = {
        'init': {
            'actions': [_clear_ids],
            'result': {'type':'state', 'state':'end'}
        }
    }
wizard_clear_ids('res.partner.clear_ids')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

