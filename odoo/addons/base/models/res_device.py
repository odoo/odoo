# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext
from datetime import datetime
import logging

import odoo
from odoo import api, fields, models, tools
from odoo.http import GeoIP, request
from odoo.tools import SQL
from .res_users import check_identity

_logger = logging.getLogger(__name__)


class ResDeviceLog(models.Model):
    _name = 'res.device.log'
    _description = 'Device Log'

    name = fields.Char("Device", required=True)
    session_identifier = fields.Char("Session Identifier", index='btree')
    platform = fields.Char("Platform")
    browser = fields.Char("Browser")
    ip_address = fields.Char("IP Address")
    country = fields.Char("Country")
    city = fields.Char("City")
    device_type = fields.Selection([('laptop', 'Laptop'), ('mobile', 'Mobile')], "Device Type")
    user_id = fields.Many2one("res.users", index='btree')
    first_activity = fields.Datetime("First Activity")
    last_activity = fields.Datetime("Last Activity", index='btree')
    exist = fields.Boolean("Exist", index='btree')
    # Note about `exist` field:
    #     If False, the session linked to the device no longer exists in the filesystem.
    #     If a user logs out, the session file still exists on the filesystem,
    #     so this field will remain set to `True`.
    #     The only way to set this field to `False` is to explicitly revoke the device.
    is_current = fields.Boolean("Current Device", compute="_compute_is_current")

    def _compute_is_current(self):
        for device in self:
            device.is_current = request and request.session.sid.startswith(device.session_identifier)

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == 'is_current':
            return SQL("session_identifier = %s DESC", request.session.sid[:42] if request else None)
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    @api.model
    def _update_device(self, request):
        """
            Must be called when we want to update the device for the current request.
            Passage through this method must leave a "trace" in the session.

            :param request: Request or WebsocketRequest object
        """
        user_agent = request.httprequest.user_agent
        platform = user_agent.platform or 'Unknown'
        browser = user_agent.browser or 'Unknown'
        ip_address = request.httprequest.remote_addr

        current_device = [platform, browser, ip_address]

        now = int(datetime.now().timestamp())
        for trace in request.session._trace:
            device, timestamp, in_db = trace
            if current_device == device:
                # If the device is not in db or logs are not up to date (i.e. not updated for one hour or more)
                if not in_db[0] or bool(now - timestamp[1] >= 3600):
                    timestamp[1] = now
                    in_db[0] = False
                    request.session.is_dirty = True
                break
        else:
            # Device doesn't exist in the session (add it)
            trace = device, timestamp, in_db = [current_device, [now, now], [False]]
            request.session._trace.append(trace)
            request.session.is_dirty = True

        if in_db[0]:
            return

        in_db[0] = True

        user_id = request.session.uid
        geoip = GeoIP(ip_address)
        name = f"{platform.capitalize()} {browser.capitalize()}"
        session_identifier = request.session.sid[:42]

        _logger.info("User %d inserts device log (%s)", user_id, session_identifier)

        if self.env.cr.readonly:
            cursor = self.env.registry.cursor(readonly=False)
        else:
            cursor = nullcontext(self.env.cr)
        with cursor as cr:
            cr.execute(SQL("""
                INSERT INTO res_device_log (name, session_identifier, platform, browser, ip_address, country, city, device_type, user_id, first_activity, last_activity, exist)
                VALUES (%(name)s, %(session_identifier)s, %(platform)s, %(browser)s, %(ip_address)s, %(country)s, %(city)s, %(device_type)s, %(user_id)s, %(first_activity)s, %(last_activity)s, %(exist)s)
            """,
                name=name,
                session_identifier=session_identifier,
                platform=platform,
                browser=browser,
                ip_address=ip_address,
                country=geoip.get('country_name'),
                city=geoip.get('city'),
                device_type='laptop' if platform.lower() not in ['android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'webos'] else 'mobile',
                user_id=user_id,
                first_activity=datetime.fromtimestamp(timestamp[0]),
                last_activity=datetime.fromtimestamp(timestamp[1]),
                exist=True,
            ))

    @api.autovacuum
    def _gc_device_log(self):
        # Keep the last device log
        # (even if the session file no longer exists on the filesystem)
        self.env.cr.execute("""
            DELETE FROM res_device_log log1
            WHERE EXISTS (
                SELECT 1 FROM res_device_log log2
                WHERE
                    log1.session_identifier = log2.session_identifier
                    AND log1.name = log2.name
                    AND log1.ip_address = log2.ip_address
                    AND log1.last_activity < log2.last_activity
            )
        """)
        _logger.info("GC device logs delete %d entries", self.env.cr.rowcount)


class ResDevice(models.Model):
    _name = "res.device"
    _inherit = ["res.device.log"]
    _description = "Devices"
    _auto = False

    @check_identity
    def revoke(self):
        return self._revoke()

    def _revoke(self):
        must_logout = bool(self.env['res.device.log'].browse(self.ids).filtered('is_current'))
        session_identifiers = list({device.session_identifier for device in self})
        odoo.http.root.session_store.delete_from_identifiers(session_identifiers)
        self.env['res.device.log'].sudo().search([('session_identifier', 'in', session_identifiers)]).exist = False
        _logger.info("User %d revokes devices (%s)", self.env.uid, ', '.join(session_identifiers))
        if must_logout:
            request.session.logout()

    @api.model
    def _select(self):
        return "SELECT DISTINCT ON (D.session_identifier, D.name, D.ip_address) D.*"

    @api.model
    def _from(self):
        return "FROM res_device_log D"

    @api.model
    def _where(self):
        return "WHERE D.exist = True"

    @api.model
    def _order_by(self):
        return "ORDER BY D.session_identifier, D.name, D.ip_address, D.last_activity DESC"

    @property
    def _query(self):
        return "%s %s %s %s" % (self._select(), self._from(), self._where(), self._order_by())

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE or REPLACE VIEW %s as (%s)
        """,
            SQL.identifier(self._table),
            SQL(self._query)
        ))
