# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2009 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

from osv import osv, fields
import pooler
import time
import math
from pprint import pprint as pp

from tools import config, debug
from tools.maintenance import remote_contract

class maintenance_contract_module(osv.osv):
    _name ="maintenance.contract.module"
    _description = "maintenance contract modules"
    _columns = {
        'name' : fields.char('Name', size=128, required=True),
        'version': fields.char('Version', size=64,),
    }

maintenance_contract_module()

class maintenance_contract(osv.osv):
    _name = "maintenance.contract"
    _description = "Maintenance Contract"

    def _get_valid_contracts(self, cr, uid):
        return [contract for contract in self.browse(cr, uid, self.search(cr, uid, [])) if contract.state == 'valid']

    def status(self, cr, uid):
        covered_modules, uncovered_modules = set(), set()

        status = 'none'
        for contract in self._get_valid_contracts(cr, uid):
            covered_modules.update([m.name for m in contract.module_ids])
        
        if covered_modules:
            modobj = self.pool.get('ir.module.module')
            modids = modobj.search(cr, uid, [('state', '=', 'installed')])
            uncovered_modules = set(m.name for m in modobj.browse(cr, uid, modids)) - covered_modules
            status = ['full', 'partial'][len(uncovered_modules) > 0]
        
        return {
            'status': status,
            'uncovered_modules': list(uncovered_modules),
        }
    
    def send(self, cr, uid, tb, explanations, remarks=None):
        assert self.status(cr, uid) == 'full'
        contract = self._get_valid_contracts(cr, uid)[0]
        
        content = "(%s) has reported the following bug:\n%s\nremarks: %s\nThe traceback is:\n%s" % (
            contract.name, explanations, remarks or '', tb
        )
        try:
            import urllib
            args = [('contract_id', contract.name),('data', content)]
            args = urllib.urlencode(args)
            fp = urllib.urlopen('http://www.openerp.com/scripts/survey.php', args)
            submit_result = fp.read()
            debug(submit_result)
            fp.close()
        except:
            # TODO schedule a retry
            return False
        return True

    def _valid_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            res[contract.id] = ("unvalid", "valid")[contract.date_stop >= time.strftime('%Y-%m-%d')]
        return res

    _columns = {
        'name' : fields.char('Contract ID', size=256, required=True, readonly=True),
        'password' : fields.char('Password', size=64, invisible=True, required=True, readonly=True),
        'date_start' : fields.date('Starting Date', readonly=True),
        'date_stop' : fields.date('Ending Date', readonly=True),
        'module_ids' : fields.many2many('maintenance.contract.module', 'maintenance_contract_module_rel', 'contract_id', 'module_id', 'Covered Modules', readonly=True),
        'state' : fields.function(_valid_get, method=True, string="State", type="selection", selection=[('valid', 'Valid'),('unvalid', 'Unvalid')], readonly=True),
        'kind' : fields.selection([('full', 'Full'),('partial', 'Partial')], 'Kind', required=True, readonly=True),
    }
    _defaults = {
        'password' : lambda obj,cr,uid,context={} : '',
    }
    _sql_constraints = [
        ('uniq_name', 'unique(name)', "Your maintenance contract is already subscribed in the system !")
    ]

maintenance_contract()


class maintenance_contract_wizard(osv.osv_memory):
    _name = 'maintenance.contract.wizard'

    _columns = {
        'name' : fields.char('Contract ID', size=256, required=True ),
        'password' : fields.char('Password', size=64, required=True),
        'state' : fields.selection([('draft', 'Draft'),('validated', 'Validated'),('unvalidated', 'Unvalidated')], 'States'),
    }

    _defaults = {
        'state' : lambda *a: 'draft',
    }

    def action_validate(self, cr, uid, ids, context):
        if not ids:
            return False

        module_proxy = self.pool.get('ir.module.module')
        module_ids = module_proxy.search(cr, uid, [('state', '=', 'installed')])
        modules = module_proxy.read(cr, uid, module_ids, ['name', 'installed_version'])

        contract = self.read(cr, uid, ids, ['name', 'password'])[0]

        contract_info = remote_contact(contract['name'], contract['password'], modules)

        is_ok = contract_info['status'] in ('partial', 'full')
        if is_ok:
            if contract_info['modules_with_contract']:
                module_ids = []
                for name, version in contract_info['modules_with_contract']:
                    contract_module = self.pool.get('maintenance.contract.module')
                    res = contract_module.search(cr, uid, [('name', '=', name),('version', '=', version)])
                    if not res:
                        id = contract_module.create(cr, uid, { 'name' : name, 'version' : version } )
                    else:
                        id = res[0]
                    module_ids.append(id)

            self.pool.get('maintenance.contract').create(
                cr, 
                uid, {
                    'name' : contract['name'],
                    'password' : contract['password'],
                    'date_start' : contract_info['date_from'],
                    'date_stop' : contract_info['date_to'],
                    'kind' : contract_info['status'],
                    'module_ids' : [(6,0,module_ids)],
                }
            )

        return self.write(cr, uid, ids, {'state' : ('unvalidated', 'validated')[is_ok] }, context=context)

maintenance_contract_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

