# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext
from datetime import datetime, timedelta
import ipaddress
import logging
import math

from odoo import api, fields, models, tools
from odoo.http import GeoIP, request, root, STORED_SESSION_BYTES
from odoo.tools import SQL, OrderedSet, unique
from odoo.tools.translate import _
from .res_users import check_identity

_logger = logging.getLogger(__name__)


def haversine_formula(latitude_A, longitude_A, latitude_B, longitude_B):
    """
        The haversine formula is used to calculate the distance between two points
        on a sphere, taking into account their latitudes and longitudes.
        :return (int): the distance between the two points in kilometers.
    """
    latitude_A = math.radians(latitude_A)
    longitude_A = math.radians(longitude_A)
    latitude_B = math.radians(latitude_B)
    longitude_B = math.radians(longitude_B)
    delta_latitude = latitude_B - latitude_A
    delta_longitude = longitude_B - longitude_A
    var_1 = math.sin(delta_latitude / 2) ** 2 \
        + math.cos(latitude_A) * math.cos(latitude_B) * math.sin(delta_longitude / 2) ** 2
    var_2 = 2 * math.atan2(math.sqrt(var_1), math.sqrt(1 - var_1))
    return math.floor(var_2 * 6371)  # 6371 = radius of Earth [km]


class ResDeviceLog(models.Model):
    _name = 'res.device.log'
    _description = 'Device Log'
    _rec_names_search = ['platform', 'browser']

    session_identifier = fields.Char("Session Identifier", required=True, index='btree')
    platform = fields.Char("Platform")
    browser = fields.Char("Browser")
    ip_address = fields.Char("IP Address")
    country = fields.Char("Country")
    city = fields.Char("City")
    device_type = fields.Selection([('computer', 'Computer'), ('mobile', 'Mobile')], "Device Type")
    user_id = fields.Many2one("res.users", index='btree')
    first_activity = fields.Datetime("First Activity")
    last_activity = fields.Datetime("Last Activity", index='btree')
    revoked = fields.Boolean("Revoked",
                            help="""If True, the session file corresponding to this device
                                    no longer exists on the filesystem.""")
    is_current = fields.Boolean("Current Device", compute="_compute_is_current")
    linked_ip_addresses = fields.Text("Linked IP address", compute="_compute_linked_ip_addresses")

    _composite_idx = models.Index("(user_id, session_identifier, platform, browser, last_activity, id) WHERE revoked IS NOT TRUE")
    _revoked_idx = models.Index("(revoked) WHERE revoked IS NOT TRUE")

    def _compute_display_name(self):
        for device in self:
            platform = device.platform or _("Unknown")
            browser = device.browser or _("Unknown")
            device.display_name = f"{platform.capitalize()} {browser.capitalize()}"

    def _compute_is_current(self):
        for device in self:
            device.is_current = request and request.session.sid.startswith(device.session_identifier)

    def _compute_linked_ip_addresses(self):
        device_group_map = {}
        for *device_info, ip_array in self.env['res.device.log']._read_group(
            domain=[('session_identifier', 'in', self.mapped('session_identifier'))],
            groupby=['session_identifier', 'platform', 'browser'],
            aggregates=['ip_address:array_agg']
        ):
            device_group_map[tuple(device_info)] = ip_array
        for device in self:
            device.linked_ip_addresses = '\n'.join(
                OrderedSet(device_group_map.get(
                    (device.session_identifier, device.platform, device.browser), []
                ))
            )

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == 'is_current' and request:
            return SQL("session_identifier = %s DESC", request.session.sid[:STORED_SESSION_BYTES])
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    def _is_mobile(self, platform):
        if not platform:
            return False
        mobile_platform = ['android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'webos']
        return platform.lower() in mobile_platform

    @api.model
    def _check_location(self, request):
        """
            Check if the location of the last trace is plausible according to
            the history of location within the session.

            This method should be called when a new trace has been added because
            it assumes that the ip address of the last trace (in the order of insertion)
            is the one to be checked.

            An IPv4 is trusted if it is located within a radius close enough to another
            IP address that has been checked beforehand.
            An IPv6 address is trusted if it contains the same 64-bit network as another
            IPv6 address that has already been verified.
            Otherwise it is tested according to location.

            If a location is not checked, we fallback to the `_alert_untrusted_location` method.
        """
        if len(request.session['_trace']) <= 1:
            return
        last_trace = request.session['_trace'][-1]

        last_ip = last_trace['ip_address']
        geoip = GeoIP(last_ip)
        last_latitude, last_longitude, last_accuracy_radius = (
            geoip.location.latitude,
            geoip.location.longitude,
            geoip.location.accuracy_radius
        )
        last_ip = ipaddress.ip_address(last_ip)

        if not (last_latitude and last_longitude and last_accuracy_radius):
            return

        number_trusted_days = int(self.env['ir.config_parameter'].sudo().get_param("base.number_trusted_days_ip", 30))
        last_activity = last_trace['last_activity']
        time_ = last_activity - int(timedelta(days=number_trusted_days).total_seconds())

        for trace in (t for t in request.session['_trace'][-2::-1] if t['last_activity'] >= time_):
            ip = trace['ip_address']
            geoip = GeoIP(ip)
            latitude, longitude, accuracy_radius = (
                geoip.location.latitude,
                geoip.location.longitude,
                geoip.location.accuracy_radius
            )
            ip = ipaddress.ip_address(ip)

            # Assume all IPv6 networks are /64, consider IPs coming from
            # a same network safe.
            if (
                isinstance(last_ip, ipaddress.IPv6Address) and
                isinstance(ip, ipaddress.IPv6Address) and
                (int(last_ip) >> 64) == (int(ip) >> 64)
            ):
                break

            if not (latitude and longitude and accuracy_radius):
                continue

            distance = haversine_formula(last_latitude, last_longitude, latitude, longitude)
            max_distance = max(accuracy_radius, last_accuracy_radius) * 1.5
            # We add a tolerance, because according to the definition of
            # the ``accuracy_radius`` attribute, the radius has a confidence of 67%.
            if distance <= max_distance:
                break  # Trusted location
        else:
            user_id = request.session.uid
            session_identifier = request.session.sid[:42]
            _logger.info("User %d used untrusted ip address %s for session identifier %s", user_id, last_ip, session_identifier)
            self.env.user._alert_untrusted_location()

    @api.model
    def _update_device(self, request):
        """
            Must be called when we want to update the device for the current request.
            Passage through this method must leave a "trace" in the session.

            :param request: Request or WebsocketRequest object
        """
        trace = request.session.update_trace(request)
        if not trace:
            return

        geoip = GeoIP(trace['ip_address'])
        user_id = request.session.uid
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]

        first_activity = datetime.fromtimestamp(trace['first_activity'])
        last_activity = datetime.fromtimestamp(trace['last_activity'])

        if self.env.cr.readonly:
            self.env.cr.rollback()
            cursor = self.env.registry.cursor(readonly=False)
        else:
            cursor = nullcontext(self.env.cr)
        with cursor as cr:
            cr.execute(SQL("""
                INSERT INTO res_device_log (session_identifier, platform, browser, ip_address, country, city, device_type, user_id, first_activity, last_activity, revoked)
                VALUES (%(session_identifier)s, %(platform)s, %(browser)s, %(ip_address)s, %(country)s, %(city)s, %(device_type)s, %(user_id)s, %(first_activity)s, %(last_activity)s, %(revoked)s)
            """,
                session_identifier=session_identifier,
                platform=trace['platform'],
                browser=trace['browser'],
                ip_address=trace['ip_address'],
                country=geoip.get('country_name'),
                city=geoip.get('city'),
                device_type='mobile' if self._is_mobile(trace['platform']) else 'computer',
                user_id=user_id,
                first_activity=first_activity,
                last_activity=last_activity,
                revoked=False,
            ))
            _logger.info("User %d inserts device log (%s)", user_id, session_identifier)
            if first_activity == last_activity:
                # New trace is categorised by a last activity which is equal
                # to the first activity (>< updated trace).
                self.with_env(self.env(cr=cr))._check_location(request)

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
                    AND log1.platform = log2.platform
                    AND log1.browser = log2.browser
                    AND log1.ip_address = log2.ip_address
                    AND log1.last_activity < log2.last_activity
            )
        """)
        _logger.info("GC device logs delete %d entries", self.env.cr.rowcount)

    @api.autovacuum
    def __update_revoked(self):
        """
            Set the field ``revoked`` to ``True`` for ``res.device.log``
            for which the session file no longer exists on the filesystem.
        """
        device_logs_by_session_identifier = {}
        for session_identifier, device_logs in self.env['res.device.log']._read_group(
            domain=[('revoked', '=', False)],
            groupby=['session_identifier'],
            aggregates=['id:recordset'],
        ):
            device_logs_by_session_identifier[session_identifier] = device_logs

        revoked_session_identifiers = root.session_store.get_missing_session_identifiers(
            device_logs_by_session_identifier.keys()
        )
        device_logs_to_revoke = self.env['res.device.log'].concat(*map(
            device_logs_by_session_identifier.get,
            revoked_session_identifiers
        ))
        # Initial run may take 5-10 minutes due to many non-revoked sessions,
        # marking them enables index use on ``revoked IS NOT TRUE``.
        device_logs_to_revoke.sudo().write({'revoked': True})


class ResDevice(models.Model):
    _name = 'res.device'
    _inherit = ["res.device.log"]
    _description = "Devices"
    _auto = False
    _order = 'last_activity desc'

    @check_identity
    def revoke(self):
        return self._revoke()

    def _revoke(self):
        ResDeviceLog = self.env['res.device.log']
        session_identifiers = list(unique(device.session_identifier for device in self))
        root.session_store.delete_from_identifiers(session_identifiers)
        revoked_devices = ResDeviceLog.sudo().search([('session_identifier', 'in', session_identifiers)])
        revoked_devices.write({'revoked': True})
        _logger.info("User %d revokes devices (%s)", self.env.uid, ', '.join(session_identifiers))

        must_logout = bool(self.filtered('is_current'))
        if must_logout:
            request.session.logout()

    @api.model
    def _select(self):
        return "SELECT D.*"

    @api.model
    def _from(self):
        return "FROM res_device_log D"

    @api.model
    def _where(self):
        return """
            WHERE
                NOT EXISTS (
                    SELECT 1
                    FROM res_device_log D2
                    WHERE
                        D2.user_id = D.user_id
                        AND D2.session_identifier = D.session_identifier
                        AND D2.platform IS NOT DISTINCT FROM D.platform
                        AND D2.browser IS NOT DISTINCT FROM D.browser
                        AND (
                            D2.last_activity > D.last_activity
                            OR (D2.last_activity = D.last_activity AND D2.id > D.id)
                        )
                        AND D2.revoked IS NOT TRUE
                )
                AND D.revoked IS NOT TRUE
        """

    @property
    def _query(self):
        return "%s %s %s" % (self._select(), self._from(), self._where())

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE or REPLACE VIEW %s as (%s)
        """,
            SQL.identifier(self._table),
            SQL(self._query)
        ))
