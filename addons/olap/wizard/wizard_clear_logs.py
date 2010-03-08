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
import time

import wizard
import pooler
from osv import osv


info = '''<?xml version="1.0"?>
<form string="Load Data">
    <label string="Logs Cleared successfully"/>
</form>'''

form1 = '''<?xml version="1.0"?>
<form string=" To Load Data">
    <field name='user_name'/>
</form>'''

field1 = {
 #   'account_id': {'string':"Analytic Account", 'type':'many2one', 'relation':'account.analytic.account', 'required':True, 'domain':"[('type','=','normal')]"},
    'user_name': {'string':'User', 'type':'char','size':'64', 'required':True, 'readonly':True},
#    'db_name': {'string':'Database Name', 'type':'char','size':'64', 'required':True, 'readonly':True},

}

def clear_logs(self,cr,uid,part,context={}):
    ids=pooler.get_pool(cr.dbname).get('olap.query.logs').search(cr,uid,[('user_id','=',uid)])
    pooler.get_pool(cr.dbname).get('olap.query.logs').unlink(cr, uid,ids,context)
    return {}

def _getdata(self,cr,uid,part,context={}):
    ids=pooler.get_pool(cr.dbname).get('res.users').browse(cr,uid,uid)
    part['form']['user_name']=ids['name']
#    part['form']['db_name']=lines.database_id.db_name
    return part['form']

class wizard_clear_logs(wizard.interface):

    states = {

       'init': {
            'actions': [_getdata],
            'result': {'type':'form','arch':form1, 'fields':field1, 'state':[('end','Cancel'),('ok','Clear Logs')]}
        },

        'ok': {
            'actions': [clear_logs],
            'result': {'type':'form','arch':info,'fields':{}, 'state':[('end','Ok')]}
                },

         'info': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','Ok')]}
                },

      }

wizard_clear_logs('olap.query.logs.clear')
