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
from tools.misc import ustr
from tools.translate import _
import tools.maintenance as tm
import tools.ping
import datetime

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

        crm_case_id = None
        rc = None
        try:
            for contract in valid_contracts: 
                rc = tm.remote_contract(cr, uid, contract.name)
                
                if rc.id:
                    contract_name = contract.name
                    break
                rc = None
        
            if not rc:
                raise osv.except_osv(_('Error'), _('Unable to find a valid contract'))
            
            origin = 'client'
            dbuuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
            crm_case_id = rc.submit_6({
                'contract_name': contract_name,
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
            res[contract.id] = ("unvalid", "valid")[contract.date_stop >= time.strftime('%Y-%m-%d')]
        return res
    
    def check_validity(self, cr, uid, ids, context={}):
        contract_id = ids[0]
        contract = self.browse(cr, uid, contract_id)
        valid = contract.state == "valid"
        
        self.send_ping(cr, uid, ids, cron_mode=False, context=context)
        
        contract = self.browse(cr, uid, contract_id)
        valid2 = contract.state == "valid"
        if not valid and not valid2:
            raise osv.except_osv("Contract validation error",
                                 "Please check your maintenance contract name and validity.")
    
    def send_ping(self, cr, uid, ids, cron_mode=True, context={}):
        try:
            result = tools.ping.send_ping(cr, uid)
        except:
            if cron_mode:
                pass # if ping fails that's bad but we don't want it to interfere
            else:
                raise osv.except_osv("Error", "Error during communication with the maintenance server.")
        
        contracts = result["validity_dates"]
        for contract in contracts:
            c_id = self.search(cr, uid, [("name","=",contract)])[0]
            date_from = contracts[contract][0]
            date_to = contracts[contract][1]
            valid = datetime.date.today() >= datetime.datetime.strptime(date_from, '%Y-%m-%d').date() \
                and datetime.date.today() <= datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            self.write(cr, uid, c_id, {
                "date_start": date_from,
                "date_stop": date_to,
                "state": "valid" if valid else "unvalid",
            })
        
        if cron_mode:
            cronosv = self.pool.get("ir.cron")
            sched_id = cronosv.search(cr, uid, [("name","=","Maintenance Update Scheduler")])[0]
            cronosv.write(cr, uid, sched_id, {
                "interval_type": result["interval_type"],
                "interval_number": result["interval_number"],
            })
        
        return True

    _columns = {
        'name' : fields.char('Contract ID', size=384, required=True),
        'date_start' : fields.date('Starting Date', readonly=True),
        'date_stop' : fields.date('Ending Date', readonly=True),
        'state' : fields.function(_valid_get, method=True, string="State", type="selection",
                                  selection=[('valid', 'Valid'),('unvalid', 'Unvalid')], readonly=True),
        'kind' : fields.char('Kind', size=64, readonly=True),
    }
    
    _defaults = {
        'state': 'unvalid',
    }
    
    _sql_constraints = [
        ('uniq_name', 'unique(name)', "Your maintenance contract is already subscribed in the system !")
    ]

maintenance_contract()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

