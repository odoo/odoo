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
import pooler
from osv import osv
import time
import sys

form = '''<?xml version="1.0"?>
<form string="Launchpad Bugs Synchronization">
    <label string="Click OK to continue synchronization with launchpad"/>
</form>'''

fields = {
}

class makeSync(wizard.interface):

    def make_sync(self, cr, uid, data, context):
        state = pooler.get_pool(cr.dbname).get('crm.case')._check_bug(cr, uid)
        if not state:
            raise osv.except_osv(_('Error'), _('Some problem occurred while making synchronization'))
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('ok','OK')]}
        },
        'ok': {
            'actions': [make_sync],
            'result': {'type':'state', 'state':'end'}
        }
    }
makeSync('lp_sync')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

