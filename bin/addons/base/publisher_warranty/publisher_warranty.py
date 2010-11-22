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
import logging
from tools.translate import _
import tools.maintenance as tm
import urllib
from tools.safe_eval import safe_eval
import pooler
from tools.config import config
import release

_logger = logging.getLogger(__name__)

class publisher_warranty_contract(osv.osv):
    _name = "publisher_warranty.contract"

    def _get_valid_contracts(self, cr, uid):
        return [contract for contract in self.browse(cr, uid, self.search(cr, uid, []))
                if contract.state == 'valid']
    
    def status(self, cr, uid):
        """ Method called by the client to check availability of publisher warranty contract. """
        
        contracts = self._get_valid_contracts(cr, uid)
        return {
            'status': "full" if contracts else "none" ,
            'uncovered_modules': list(),
        }
    
    def send(self, cr, uid, tb, explanations, remarks=None):
        """ Method called by the client to send a problem to the publisher warranty server. """
        
        if not remarks:
            remarks = ""

        valid_contracts = self._get_valid_contracts(cr, uid)
        valid_contract = valid_contracts[0]
        
        try:
            rc = tm.remote_contract(cr, uid, valid_contract.name)
                
            origin = 'client'
            dbuuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
            crm_case_id = rc.submit_6({
                'contract_name': valid_contract.name,
                'tb': tb,
                'explanations': explanations,
                'remarks': remarks,
                'origin': origin,
                'dbname': cr.dbname,
                'dbuuid': dbuuid})
            
            if not crm_case_id:
                return False
            
        except osv.except_osv:
            raise
        except:
            _logger.warning("Error sending problem report", exc_info=1)
            raise osv.except_osv("Connection error", "An error occured during the connection " +
                                 "with the publisher warranty server.")
        
        return True
    
    def check_validity(self, cr, uid, ids, context={}):
        contract_id = ids[0]
        contract = self.browse(cr, uid, contract_id)
        state = contract.state
        validated = state != "unvalidated"
        
        self.send_ping(cr, uid, ids, cron_mode=False, context=context)
        
        contract = self.browse(cr, uid, contract_id)
        validated2 = contract.state != "unvalidated"
        if not validated and not validated2:
            raise osv.except_osv(_("Contract validation error"),
                                 _("Please check your publisher warranty contract name and validity."))
    
    def send_ping(self, cr, uid, ids, cron_mode=True, context={}):
        try:
            try:
                result = send_ping(cr, uid)
            except:
                _logger.debug("Exception while sending a ping", exc_info=1)
                raise osv.except_osv(_("Error"), _("Error during communication with the publisher warranty server."))
            
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
            _logger.debug("Exception while interpreting the result of a ping", exc_info=1)
            if cron_mode:
                return False # same as before
            else:
                raise
            
        return True

    _columns = {
        'name' : fields.char('Contract Name', size=384, required=True),
        'date_start' : fields.date('Starting Date', readonly=True),
        'date_stop' : fields.date('Ending Date', readonly=True),
        'state' : fields.selection([('unvalidated', 'Unvalidated'), ('valid', 'Valid')
                            , ('terminated', 'Terminated'), ('canceled', 'Canceled')], string="State", readonly=True),
        'kind' : fields.char('Kind', size=64, readonly=True),
    }
    
    _defaults = {
        'state': 'unvalidated',
    }
    
    _sql_constraints = [
        ('uniq_name', 'unique(name)', "Your publisher warranty contract is already subscribed in the system !")
    ]

publisher_warranty_contract()

class maintenance_contract(osv.osv_memory):
    """ Old osv we only keep for compatibility with the clients. """
    
    _name = "maintenance.contract"
    
    def status(self, cr, uid):
        return self.pool.get("publisher_warranty.contract").status(cr, uid)
        
    def send(self, cr, uid, tb, explanations, remarks=None):
        return self.pool.get("publisher_warranty.contract").send(cr, uid, tb, explanations, remarks)
    
maintenance_contract()

class publisher_warranty_contract_wizard(osv.osv_memory):
    _name = 'publisher_warranty.contract.wizard'

    _columns = {
        'name' : fields.char('Contract Name', size=256, required=True ),
    }

    def action_validate(self, cr, uid, ids, context=None):
        if not ids:
            return False

        wiz = self.browse(cr, uid, ids[0])
        c_name = wiz.name
        
        contract_osv = self.pool.get("publisher_warranty.contract")
        contracts = contract_osv.search(cr, uid, [("name","=",c_name)])
        if contracts:
            raise osv.except_osv(_("Error"), _("That contract is already registered in the system."))
        
        contract_id = contract_osv.create(cr, uid, {
            "name": c_name,
            "state": "unvalidated",
        })
        
        contract_osv.check_validity(cr, uid, [contract_id])
        
        return {'type': 'ir.actions.act_window_close'}

publisher_warranty_contract_wizard()

def send_ping(cr, uid):
    pool = pooler.get_pool(cr.dbname)
    
    dbuuid = pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
    nbr_users = pool.get("res.users").search(cr, uid, [], count=True)
    contractosv = pool.get('publisher_warranty.contract')
    contracts = contractosv.browse(cr, uid, contractosv.search(cr, uid, []))
    msg = {
        "dbuuid": dbuuid,
        "nbr_users": nbr_users,
        "dbname": cr.dbname,
        "version": release.version,
        "contracts": [c.name for c in contracts],
    }
    
    uo = urllib.urlopen(config.get("publisher_warranty_url"),
                        urllib.urlencode({'arg0': msg, "action": "update",}))
    try:
        submit_result = uo.read()
    finally:
        uo.close()
    
    result = safe_eval(submit_result)
    
    return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

