# -*- coding: utf-8 -*-
from ast import literal_eval
import datetime
from functools import partial
import logging
import werkzeug.urls
import urllib2

from openerp import release, SUPERUSER_ID
from openerp.models import AbstractModel
from openerp.tools.translate import _
from openerp.tools.config import config
from openerp.tools import misc
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class publisher_warranty_contract(AbstractModel):
    _name = "publisher_warranty.contract"

    def _get_message(self, cr, uid):
        Users = self.pool['res.users']
        user_count = partial(Users.search_count, cr, uid)
        get_param = partial(self.pool['ir.config_parameter'].get_param, cr, SUPERUSER_ID)

        dbuuid = get_param('database.uuid')
        db_create_date = get_param('database.create_date')
        limit_date = datetime.datetime.now()
        limit_date = limit_date - datetime.timedelta(15)
        limit_date_str = limit_date.strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
        nbr_users = user_count([])
        nbr_active_users = user_count([("login_date", ">=", limit_date_str)])
        nbr_share_users = 0
        nbr_active_share_users = 0
        if "share" in Users._fields:
            nbr_share_users = user_count([("share", "=", True)])
            nbr_active_share_users = user_count([("share", "=", True), ("login_date", ">=", limit_date_str)])
        user = Users.browse(cr, uid, uid)
        domain = [('application', '=', True), ('state', 'in', ['installed', 'to upgrade', 'to remove'])]
        apps = self.pool['ir.module.module'].search_read(cr, SUPERUSER_ID, domain, ['name'])

        enterprise_code = get_param('database.enterprise_code')

        web_base_url = get_param('web.base.url')
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
            "apps": [app['name'] for app in apps],
            "enterprise_code": enterprise_code,
        }
        if user.partner_id.company_id:
            company_id = user.partner_id.company_id.id
            msg.update(self.pool["res.company"].read(cr, uid, [company_id], ["name", "email", "phone"])[0])
        return msg

    def _get_sys_logs(self, cr, uid):
        """
        Utility method to send a publisher warranty get logs messages.
        """
        msg = self._get_message(cr, uid)
        arguments = {'arg0': msg, "action": "update"}
        arguments_raw = werkzeug.urls.url_encode(arguments)

        url = config.get("publisher_warranty_url")

        uo = urllib2.urlopen(url, arguments_raw, timeout=30)
        try:
            submit_result = uo.read()
            return literal_eval(submit_result)
        finally:
            uo.close()

    def update_notification(self, cr, uid, ids, cron_mode=True, context=None):
        """
        Send a message to OpenERP's publisher warranty server to check the
        validity of the contracts, get notifications, etc...

        @param cron_mode: If true, catch all exceptions (appropriate for usage in a cron).
        @type cron_mode: boolean
        """
        try:
            try:
                result = self._get_sys_logs(cr, uid)
            except Exception:
                if cron_mode:   # we don't want to see any stack trace in cron
                    return False
                _logger.debug("Exception while sending a get logs messages", exc_info=1)
                raise UserError(_("Error during communication with the publisher warranty server."))
            # old behavior based on res.log; now on mail.message, that is not necessarily installed
            IMD = self.pool['ir.model.data']
            user = self.pool['res.users'].browse(cr, SUPERUSER_ID, SUPERUSER_ID)
            poster = IMD.xmlid_to_object(cr, SUPERUSER_ID, 'mail.channel_all_employees', context=context)
            if not (poster and poster.exists()):
                if not user.exists():
                    return True
                poster = user
            for message in result["messages"]:
                try:
                    poster.message_post(body=message, subtype='mt_comment', partner_ids=[user.partner_id.id])
                except Exception:
                    pass
            if result.get('enterprise_info'):
                # Update expiration date
                self.pool['ir.config_parameter'].set_param(cr, SUPERUSER_ID, 'database.expiration_date', result['enterprise_info'].get('expiration_date'), ['base.group_user'])
                self.pool['ir.config_parameter'].set_param(cr, SUPERUSER_ID, 'database.expiration_reason', result['enterprise_info'].get('expiration_reason', 'trial'), ['base.group_system'])
                self.pool['ir.config_parameter'].set_param(cr, SUPERUSER_ID, 'database.enterprise_code', result['enterprise_info'].get('enterprise_code'), ['base.group_user'])

        except Exception:
            if cron_mode:
                return False    # we don't want to see any stack trace in cron
            else:
                raise
        return True
