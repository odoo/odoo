# -*- coding: utf-8 -*-
import datetime
import logging
import sys
import urllib
import urllib2

from openerp import pooler
from openerp import release
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from openerp.tools.config import config
from openerp.tools import misc

_logger = logging.getLogger(__name__)

"""
Time interval that will be used to determine up to which date we will
check the logs to see if a message we just received was already logged.
@type: datetime.timedelta
"""
_PREVIOUS_LOG_CHECK = datetime.timedelta(days=365)

def get_sys_logs(self, cr, uid):
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
    nbr_active_users = pool.get("res.users").search(cr, uid, [("login_date", ">=", limit_date_str)], count=True)
    nbr_share_users = False
    nbr_active_share_users = False
    if "share" in pool.get("res.users")._all_columns:
        nbr_share_users = pool.get("res.users").search(cr, uid, [("share", "=", True)], count=True)
        nbr_active_share_users = pool.get("res.users").search(cr, uid, [("share", "=", True), ("login_date", ">=", limit_date_str)], count=True)
    user = pool.get("res.users").browse(cr, uid, uid)

    web_base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', 'False')
    msg = {
        "dbuuid": dbuuid,
        "nbr_users": nbr_users,
        "nbr_active_users": nbr_active_users,
        "nbr_share_users": nbr_share_users,
        "nbr_active_share_users": nbr_active_share_users,
        "dbname": cr.dbname,
        "db_create_date": db_create_date,
        "version": release.version,
        "language": user.lang,
        "web_base_url": web_base_url,
    }
    msg.update(pool.get("res.company").read(cr,uid,[1],["name","email","phone"])[0])

    add_arg = {"timeout":30} if sys.version_info >= (2,6) else {}
    arguments = {'arg0': msg, "action": "update",}
    arguments_raw = urllib.urlencode(arguments)

    url = config.get("publisher_warranty_url")

    uo = urllib2.urlopen(url, arguments_raw, **add_arg)
    result = {}
    try:
        submit_result = uo.read()
        result = safe_eval(submit_result)
    finally:
        uo.close()
    return result

class publisher_warranty_contract(osv.osv):
    _name = "publisher_warranty.contract"

    def update_notification(self, cr, uid, ids, cron_mode=True, context=None):
        """
        Send a message to OpenERP's publisher warranty server to check the
        validity of the contracts, get notifications, etc...

        @param cron_mode: If true, catch all exceptions (appropriate for usage in a cron).
        @type cron_mode: boolean
        """
        try:
            try:
                result = get_sys_logs(self, cr, uid)
            except Exception, ex:
                if cron_mode: # we don't want to see any stack trace in cron
                    return False
                _logger.debug("Exception while sending a get logs messages", exc_info=1)
                raise osv.except_osv(_("Error"), _("Error during communication with the publisher warranty server."))
            limit_date = (datetime.datetime.now() - _PREVIOUS_LOG_CHECK).strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
            # old behavior based on res.log; now on mail.message, that is not necessarily installed
            proxy = self.pool.get('mail.message')

            model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'group_all_employees')

            for message in result["messages"]:
                values = {
                    'body' : message,
                    'model' : 'mail.group',
                    'res_id' : res_id,
                    'user_id' : False,
                }
                proxy.create(cr, uid, values, context=context)
        except Exception:
            if cron_mode:
                return False # we don't want to see any stack trace in cron
            else:
                raise
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

