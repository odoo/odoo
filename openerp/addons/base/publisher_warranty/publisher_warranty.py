# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 OpenERP S.A. (<http://www.openerp.com>).
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
"""
Module to handle publisher warranty contracts as well as notifications from
OpenERP.
"""

import datetime
import logging
import sys
import urllib
import urllib2

import pooler
import release
from osv import osv, fields
from tools.translate import _
from tools.safe_eval import safe_eval
from tools.config import config
from tools import misc

_logger = logging.getLogger(__name__)

"""
Time interval that will be used to determine up to which date we will
check the logs to see if a message we just received was already logged.
@type: datetime.timedelta
"""
_PREVIOUS_LOG_CHECK = datetime.timedelta(days=365)

class publisher_warranty_contract(osv.osv):
    """
    Osv representing a publisher warranty contract.
    """
    _name = "publisher_warranty.contract"

    def _get_valid_contracts(self, cr, uid):
        """
        Return the list of the valid contracts encoded in the system.

        @return: A list of contracts
        @rtype: list of publisher_warranty.contract browse records
        """
        return [contract for contract in self.browse(cr, uid, self.search(cr, uid, []))
                if contract.state == 'valid']

    def status(self, cr, uid):
        """ Method called by the client to check availability of publisher warranty contract. """

        contracts = self._get_valid_contracts(cr, uid)
        return {
            'status': "full" if contracts else "none" ,
            'uncovered_modules': list(),
        }

    def send(self, cr, uid, tb, explanations, remarks=None, issue_name=None):
        """ Method called by the client to send a problem to the publisher warranty server. """

        if not remarks:
            remarks = ""

        valid_contracts = self._get_valid_contracts(cr, uid)
        valid_contract = valid_contracts[0]

        try:
            origin = 'client'
            dbuuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
            db_create_date = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.create_date')
            user = self.pool.get("res.users").browse(cr, uid, uid)
            user_name = user.name
            email = user.email

            msg = {'contract_name': valid_contract.name,
                'tb': tb,
                'explanations': explanations,
                'remarks': remarks,
                'origin': origin,
                'dbname': cr.dbname,
                'dbuuid': dbuuid,
                'db_create_date': db_create_date,
                'issue_name': issue_name,
                'email': email,
                'user_name': user_name,
            }


            add_arg = {"timeout":30} if sys.version_info >= (2,6) else {}
            uo = urllib2.urlopen(config.get("publisher_warranty_url"),
                                    urllib.urlencode({'arg0': msg, "action": "send",}),**add_arg)
            try:
                submit_result = uo.read()
            finally:
                uo.close()

            result = safe_eval(submit_result)

            crm_case_id = result

            if not crm_case_id:
                return False

        except osv.except_osv:
            raise
        except Exception:
            _logger.warning("Error sending problem report", exc_info=1)
            raise osv.except_osv(_("Error"),
                                 _("Error during communication with the publisher warranty server."))

        return True

    def check_validity(self, cr, uid, ids, context=None):
        """
        Check the validity of a publisher warranty contract. This method just call get_logs() but checks
        some more things, so it can be called from a user interface.
        """
        contract_id = ids[0]
        contract = self.browse(cr, uid, contract_id)
        state = contract.state
        validated = state != "unvalidated"

        self.get_logs(cr, uid, ids, cron_mode=False, context=context)

        contract = self.browse(cr, uid, contract_id)
        validated2 = contract.state != "unvalidated"
        if not validated and not validated2:
            raise osv.except_osv(_("Contract validation error"),
                                 _("Please verify your publisher warranty serial number and validity."))
        return True

    def get_logs(self, cr, uid, ids, cron_mode=True, context=None):
        """
        Send a message to OpenERP's publisher warranty server to check the validity of
        the contracts, get notifications, etc...

        @param cron_mode: If true, catch all exceptions (appropriate for usage in a cron).
        @type cron_mode: boolean
        """
        try:
            try:
                result = get_sys_logs(cr, uid)
            except Exception:
                if cron_mode: # we don't want to see any stack trace in cron
                    return False
                _logger.debug("Exception while sending a get logs messages", exc_info=1)
                raise osv.except_osv(_("Error"), _("Error during communication with the publisher warranty server."))

            contracts = result["contracts"]
            for contract in contracts:
                c_id = self.search(cr, uid, [("name","=",contract)])[0]
                # for backward compatibility
                if type(contracts[contract]) == tuple:
                    self.write(cr, uid, c_id, {
                        "date_start": contracts[contract][0],
                        "date_stop": contracts[contract][1],
                        "state": contracts[contract][2],
                        "check_support": False,
                        "check_opw": False,
                        "kind": "",
                    })
                else:
                    self.write(cr, uid, c_id, {
                        "date_start": contracts[contract]["date_from"],
                        "date_stop": contracts[contract]["date_to"],
                        "state": contracts[contract]["state"],
                        "check_support": contracts[contract]["check_support"],
                        "check_opw": contracts[contract]["check_opw"],
                        "kind": contracts[contract]["kind"],
                    })


            limit_date = (datetime.datetime.now() - _PREVIOUS_LOG_CHECK).strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
            
            # old behavior based on res.log; now on mail.message, that is not necessarily installed
            mail_message_obj = self.pool.get('mail.message')
            if mail_message_obj:
                for message in result["messages"]:
                    ids = mail_message_obj.search(cr, uid, [("model", "=", "publisher_warranty.contract"),
                                                                        ("create_date", ">=", limit_date),
                                                                        ("body_text", "=", message)])
                    if ids:
                        continue
                    mail_message_obj.create(cr, uid, {
                                    'name': message,
                                    'model': "publisher_warranty.contract",
                                    'user_id': False,
                                    }, context=context)
        except Exception:
            if cron_mode:
                return False # we don't want to see any stack trace in cron
            else:
                raise
        return True

    def get_last_user_messages(self, cr, uid, limit, context=None):
        """
        Get the messages to be written in the web client.
        @return: A list of html messages with ids, can be False or empty.
        @rtype: list of tuples(int,string)
        """
        if not self.pool.get('mail.message'):
            return []
        ids = self.pool.get('mail.message').search(cr, uid, [("model", "=", "publisher_warranty.contract")]
                                                            , order="create_date desc", limit=limit, context=context)
        if not ids:
            return []
        messages = [(x.id, x.name) for x in self.pool.get('mail.message').browse(cr, uid, ids, context=context)]
        return messages

    _columns = {
        'name' : fields.char('Serial Key', size=384, required=True, help="Your OpenERP Publisher's Warranty Contract unique key, also called serial number."),
        'date_start' : fields.date('Starting Date', readonly=True),
        'date_stop' : fields.date('Ending Date', readonly=True),
        'state' : fields.selection([('unvalidated', 'Unvalidated'), ('valid', 'Valid')
                            , ('terminated', 'Terminated'), ('canceled', 'Canceled')], string="State", readonly=True),
        'kind' : fields.char('Contract Category', size=64, readonly=True),
        "check_support": fields.boolean("Support Level 1", readonly=True),
        "check_opw": fields.boolean("OPW", readonly=True, help="Checked if this is an OpenERP Publisher's Warranty contract (versus older contract types"),
    }

    _defaults = {
        'state': 'unvalidated',
    }

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "That contract is already registered in the system.")
    ]

publisher_warranty_contract()

class maintenance_contract(osv.osv_memory):
    """ Old osv we only keep for compatibility with the clients. """

    _name = "maintenance.contract"

    def status(self, cr, uid):
        return self.pool.get("publisher_warranty.contract").status(cr, uid)

    def send(self, cr, uid, tb, explanations, remarks=None, issue_name=None):
        return self.pool.get("publisher_warranty.contract").send(cr, uid, tb,
                        explanations, remarks, issue_name)

maintenance_contract()

class publisher_warranty_contract_wizard(osv.osv_memory):
    """
    A wizard osv to help people entering a publisher warranty contract.
    """
    _name = 'publisher_warranty.contract.wizard'
    _inherit = "ir.wizard.screen"

    _columns = {
        'name' : fields.char('Serial Key', size=256, required=True, help="Your OpenERP Publisher's Warranty Contract unique key, also called serial number."),
        'state' : fields.selection([("draft", "Draft"), ("finished", "Finished")])
    }

    _defaults = {
        "state": "draft",
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

        self.write(cr, uid, ids, {"state": "finished"})

        # We should return an action ?
        return True


publisher_warranty_contract_wizard()

def get_sys_logs(cr, uid):
    """
    Utility method to send a publisher warranty get logs messages.
    """
    pool = pooler.get_pool(cr.dbname)

    dbuuid = pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
    db_create_date = pool.get('ir.config_parameter').get_param(cr, uid, 'database.create_date')
    limit_date = datetime.datetime.now()
    limit_date = limit_date - datetime.timedelta(15)
    limit_date_str = limit_date.strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
    nbr_users = pool.get("res.users").search(cr, uid, [], count=True)
    nbr_active_users = pool.get("res.users").search(cr, uid, [("date", ">=", limit_date_str)], count=True)
    nbr_share_users = False
    nbr_active_share_users = False
    if "share" in pool.get("res.users")._all_columns:
        nbr_share_users = pool.get("res.users").search(cr, uid, [("share", "=", True)], count=True)
        nbr_active_share_users = pool.get("res.users").search(cr, uid, [("share", "=", True), ("date", ">=", limit_date_str)], count=True)
    contractosv = pool.get('publisher_warranty.contract')
    contracts = contractosv.browse(cr, uid, contractosv.search(cr, uid, []))
    user = pool.get("res.users").browse(cr, uid, uid)
    msg = {
        "dbuuid": dbuuid,
        "nbr_users": nbr_users,
        "nbr_active_users": nbr_active_users,
        "nbr_share_users": nbr_share_users,
        "nbr_active_share_users": nbr_active_share_users,
        "dbname": cr.dbname,
        "db_create_date": db_create_date,
        "version": release.version,
        "contracts": [c.name for c in contracts],
        "language": user.lang,
    }

    add_arg = {"timeout":30} if sys.version_info >= (2,6) else {}
    arguments = {'arg0': msg, "action": "update",}
    arguments_raw = urllib.urlencode(arguments)
    url = config.get("publisher_warranty_url")
    uo = urllib2.urlopen(url, arguments_raw, **add_arg)
    try:
        submit_result = uo.read()
    finally:
        uo.close()

    result = safe_eval(submit_result) if submit_result else {}

    return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

