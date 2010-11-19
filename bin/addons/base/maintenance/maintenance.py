# -*- coding: utf-8 -*-
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

from osv import osv, fields
import time
import netsvc
from tools.translate import _
import tools.maintenance as tm
import tools.ping
from tools import misc

_nlogger = netsvc.Logger()
_CHAN = __name__.split()[-1]

class maintenance_contract(osv.osv):
    _name = "maintenance.contract"
    
    _description = "Maintenance Contract"

    def _get_valid_contracts(self, cr, uid):
        return [contract for contract in self.browse(cr, uid, self.search(cr, uid, [])) if contract.state == 'valid']
    
    def status(self, cr, uid):
        """ Method called by the client to check availability of maintenance contract. """
        
        contracts = self._get_valid_contracts(cr, uid)
        return {
            'status': "full" if contracts else "none" ,
            'uncovered_modules': list(),
        }
    
    def send(self, cr, uid, tb, explanations, remarks=None):
        """ Method called by the client to send a problem to the maintenance server. """
        
        if not remarks:
            remarks = ""

        valid_contracts = self._get_valid_contracts(cr, uid)
        valid_contract = valid_contracts[0]
        
        try:
            rc = tm.remote_contract(cr, uid, valid_contract.name)
                
            origin = 'client'
            dbuuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
            crm_case_id = rc.submit_6({
                'contract_name': valid_contract[0],
                'tb': tb,
                'explanations': explanations,
                'remarks': remarks,
                'origin': origin,
                'dbname': cr.dbname,
                'dbuuid': dbuuid})
        except tm.RemoteContractException, rce:
            _nlogger.notifyChannel(_CHAN, netsvc.LOG_INFO, rce)
        except osv.except_osv:
            raise
        except:
            pass # we don't want to throw exceptions in an exception handler
        
        if not crm_case_id:
            return False
        return True

    def _valid_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            res[contract.id] = ("unvalid", "valid")[contract.date_stop >= time.strftime(misc.DEFAULT_SERVER_DATE_FORMAT)]
        return res
    
    def check_validity(self, cr, uid, ids, context={}):
        contract_id = ids[0]
        contract = self.browse(cr, uid, contract_id)
        validated = contract.state != "unvalidated"
        
        self.send_ping(cr, uid, ids, cron_mode=False, context=context)
        
        contract = self.browse(cr, uid, contract_id)
        validated2 = contract.state != "unvalidated"
        if not validated and not validated2:
            raise osv.except_osv(_("Contract validation error"),
                                 _("Please check your maintenance contract name and validity."))
    
    def send_ping(self, cr, uid, ids, cron_mode=True, context={}):
        try:
            try:
                result = tools.ping.send_ping(cr, uid)
            except:
                raise osv.except_osv(_("Error"), _("Error during communication with the maintenance server."))
            
            contracts = result["contracts"]
            for contract in contracts:
                c_id = self.search(cr, uid, [("name","=",contract)])[0]
                date_from = contracts[contract][0]
                date_to = contracts[contract][1]
                state = contracts[contract][2]
                self.write(cr, uid, c_id, {
                    "date_start": date_from,
                    "date_stop": date_to,
                    "state": state,
                })
            
            if cron_mode and result["interval_type"] and result["interval_number"]:
                modosv = self.pool.get("ir.model.data")
                sched_id = modosv.get_object_reference(cr, uid, "base", "ir_cron_ping_scheduler")[1]
                cronosv = self.pool.get("ir.cron")
                cronosv.write(cr, uid, sched_id, {
                    "interval_type": result["interval_type"],
                    "interval_number": result["interval_number"],
                })
        except:
            if cron_mode:
                return False # if ping fails we don't want it to interfere
            else:
                raise
            
        return True

    _columns = {
        'name' : fields.char('Contract ID', size=384, required=True),
        'date_start' : fields.date('Starting Date', readonly=True),
        'date_stop' : fields.date('Ending Date', readonly=True),
        'state' : fields.function(_valid_get, method=True, string="State", type="selection",
                                  selection=[('unvalidated', 'Unvalidated'), ('valid', 'Valid')
                                             , ('terminated', 'Terminated'), ('canceled', 'Canceled')], readonly=True),
        'kind' : fields.char('Kind', size=64, readonly=True),
    }
    
    _defaults = {
        'state': 'unvalidated',
    }
    
    _sql_constraints = [
        ('uniq_name', 'unique(name)', "Your maintenance contract is already subscribed in the system !")
    ]

maintenance_contract()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

