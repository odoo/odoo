# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext
from datetime import datetime
import logging

from odoo import api, fields, models, tools
from odoo.http import GeoIP, request, root, STORED_SESSION_BYTES
from odoo.tools import SQL, str2bool, unique
from odoo.tools.translate import _
from odoo.tools._vendor.useragents import UserAgent
from .res_users import check_identity

_logger = logging.getLogger(__name__)


class ResDeviceLog(models.Model):
    _name = 'res.device.log'
    _description = 'Device Log'
    _rec_names_search = ['user_agent', 'ip_address']

    # Fields that identify a session
    session_identifier = fields.Char("Session Identifier", required=True, index='btree')
    user_id = fields.Many2one("res.users", required=True, index='btree')
    # Fields that identify a device for a given session (comes from the HTTP request)
    user_agent = fields.Char("User Agent", required=True)
    ip_address = fields.Char("IP Address", required=True)
    fingerprint = fields.Char("Fingerprint", required=True)
    # Fields representing the device's activity
    first_activity = fields.Datetime("First Activity", required=True)
    last_activity = fields.Datetime("Last Activity", required=True, index='btree')
    # Field that determine the "status" of the session/device on disk
    revoked = fields.Boolean("Revoked",
                            help="""If True, the session file corresponding to this device
                                    no longer exists on the filesystem.""")
    # Fields for reporting suspicious activities
    suspicious = fields.Boolean("Suspicious",
                            help="""If True, the session was used with a suspicious device.""")
    suspicious_fingerprint = fields.Boolean("Suspicious Fingerprint")
    suspicious_device = fields.Boolean("Suspicious Device")

    _composite_idx = models.Index("(session_identifier, user_agent, ip_address, fingerprint) WHERE revoked IS NOT TRUE")
    _revoked_idx = models.Index("(revoked) WHERE revoked IS NOT TRUE")

    @api.model
    def _update_device(self, request):
        """
            Must be called when we want to update the device for the current request.
            Passage through this method must leave a "trace" in the session.

            :param request: Request or WebsocketRequest object
        """
        session = request.session

        trace, suspicious_reasons = session.update_trace(request)
        if not trace:
            return
        (user_agent, ip_address, fingerprint), (first_activity, last_activity) = trace

        session_identifier = session.sid[:STORED_SESSION_BYTES]
        user_id = session.uid

        # Log suspicious activity
        suspicious_device = False
        suspicious_fingerprint = False
        if suspicious_reasons:
            if 'fingerprint' in suspicious_reasons:
                suspicious_fingerprint = str2bool(self.env['ir.config_parameter'].sudo().get_param('res_device.enable_fingerprint', default=True))
                if fingerprint:
                    _logger.info(
                        "User %d used untrusted device with fingerprint %s instead of %s for session identifier %s",
                        user_id, fingerprint, session['_fingerprint'], session_identifier,
                    )
                else:
                    _logger.info(
                        "User %d used untrusted device without fingerprint for session %s (expected fingerprint: %s)",
                        user_id, session_identifier, session['_fingerprint'],
                    )
            if 'device' in suspicious_reasons:
                suspicious_device = True
                _logger.info(
                    "User %d used untrusted device with user agent: %s and ip address: %s for session identifier %s",
                    user_id, user_agent, ip_address, session_identifier,
                )

        if self.env.cr.readonly:
            self.env.cr.rollback()
            cursor = self.env.registry.cursor(readonly=False)
        else:
            cursor = nullcontext(self.env.cr)
        with cursor as cr:
            cr.execute(SQL("""
                INSERT INTO res_device_log (session_identifier, user_id, user_agent, ip_address, fingerprint, first_activity, last_activity, revoked, suspicious, suspicious_fingerprint, suspicious_device)
                VALUES (%(session_identifier)s, %(user_id)s, %(user_agent)s, %(ip_address)s, %(fingerprint)s, %(first_activity)s, %(last_activity)s, %(revoked)s, %(suspicious)s, %(suspicious_fingerprint)s, %(suspicious_device)s)
            """,
                session_identifier=session_identifier,
                user_id=user_id,
                user_agent=user_agent,
                fingerprint=fingerprint,
                ip_address=ip_address,
                first_activity=datetime.fromtimestamp(first_activity),
                last_activity=datetime.fromtimestamp(last_activity),
                revoked=False,
                suspicious=bool(suspicious_fingerprint or suspicious_device),
                suspicious_fingerprint=suspicious_fingerprint,
                suspicious_device=suspicious_device,
            ))
            _logger.info("User %d inserts device log for session identifier %s", user_id, session_identifier)

            # TODO: automatic actions if suspicious ? (send email, session logout, ...)
            # It is necessary to have practical feedback.

    @api.autovacuum
    def _gc_device_log(self):
        # Keep the last device log (keep all suspicious logs)
        # (even if the session file no longer exists on the filesystem)
        self.env.cr.execute("""
            DELETE FROM res_device_log log1
            WHERE EXISTS (
                SELECT 1 FROM res_device_log log2
                WHERE
                    log1.session_identifier = log2.session_identifier
                    AND log1.user_agent = log2.user_agent
                    AND log1.ip_address = log2.ip_address
                    AND log1.fingerprint = log2.fingerprint
                    AND log1.last_activity < log2.last_activity
            ) AND log1.suspicious IS NOT TRUE
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


class ResDeviceLine(models.Model):
    _name = 'res.device.line'
    _description = 'Device'
    _auto = False

    session_identifier = fields.Char('Session identifier', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)

    user_agent = fields.Char('User Agent', readonly=True)
    ip_address = fields.Char('IP Address', readonly=True)
    first_activity = fields.Datetime('First Activity', readonly=True)
    last_activity = fields.Datetime('Last Activity', readonly=True)
    suspicious = fields.Boolean('Suspicious', readonly=True)
    suspicious_fingerprint = fields.Boolean('Suspicious Fingerprint', readonly=True)
    suspicious_device = fields.Boolean('Suspicious Device', readonly=True)

    fingerprint = fields.Char('Fingerprint', compute='_compute_fingerprint', readonly=True)

    platform = fields.Char('Platform', compute='_compute_info', readonly=True)
    browser = fields.Char('Browser', compute='_compute_info', readonly=True)
    browser_version = fields.Char('Browser Version', compute='_compute_info', readonly=True)
    browser_language = fields.Char('Browser Language', compute='_compute_info', readonly=True)
    device_type = fields.Char('Type', compute='_compute_info', readonly=True)
    country = fields.Char('Country', compute='_compute_info', readonly=True)
    city = fields.Char('City', compute='_compute_info', readonly=True)

    def _compute_fingerprint(self):
        device_map = {}
        for *device_group, fingerprints in self.env['res.device.log']._read_group(
            domain=[
                ('session_identifier', 'in', self.mapped('session_identifier')),
            ],
            groupby=['user_agent', 'ip_address'],
            aggregates=['fingerprint:array_agg'],
        ):
            fingerprints = set(fingerprints)
            fingerprints.discard('')
            device_map[tuple(device_group)] = '\n'.join(fingerprints)

        for device in self:
            device.fingerprint = device_map[device.user_agent, device.ip_address]

    def _compute_info(self):
        user_agent_parser = UserAgent._parser
        mobile_platform = ('android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'webos')

        for device in self:
            device.platform, device.browser, device.browser_version, device.browser_language = user_agent_parser(device.user_agent)
            geoip = GeoIP(device.ip_address)
            device.device_type = 'mobile' if device.platform in mobile_platform else 'computer'
            device.country = geoip.get('country_name') or _("Unknown")
            device.city = geoip.get('city') or _("Unknown")

    @property
    def _query(self):
        return """
            SELECT
                MIN(L.id) as id,
                L.session_identifier as session_identifier,
                MIN(L.user_id) as user_id,
                L.user_agent as user_agent,
                L.ip_address as ip_address,
                MIN(L.first_activity) as first_activity,
                MAX(L.last_activity) as last_activity,
                bool_or(L.suspicious) as suspicious,
                bool_or(L.suspicious_fingerprint) as suspicious_fingerprint,
                bool_or(L.suspicious_device) as suspicious_device
            FROM
                res_device_log L
            WHERE
                L.revoked IS NOT TRUE
            GROUP BY
                session_identifier,
                user_agent,
                ip_address
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE or REPLACE VIEW %s as (%s)
        """,
            SQL.identifier(self._table),
            SQL(self._query),
        ))

    @check_identity
    def mark_as_not_suspicious(self):
        return self._mark_as_not_suspicious()

    def _mark_as_not_suspicious(self):
        self = self.filtered('suspicious')  # noqa: PLW0642
        if not self:
            return

        device_map = {}
        for *device_group, device_log_ids in self.env['res.device.log']._read_group(
            domain=[
                ('session_identifier', 'in', self.mapped('session_identifier')),
                ('suspicious', '=', True),
            ],
            groupby=['user_agent', 'ip_address'],
            aggregates=['id:recordset'],
        ):
            device_map[tuple(device_group)] = device_log_ids

        device_log_to_trust = self.env['res.device.log']
        for device in self:
            device_log_to_trust += device_map[device.user_agent, device.ip_address]

        device_log_to_trust.sudo().write({'suspicious': False})


class ResDevice(models.Model):
    _name = 'res.device'
    _description = 'Session Device'
    _auto = False

    session_identifier = fields.Char('Session identifier')
    user_id = fields.Many2one('res.users', string='User', readonly=True)

    first_activity = fields.Datetime('First Activity', readonly=True)
    last_activity = fields.Datetime('Last Activity', readonly=True)
    suspicious = fields.Boolean('Suspicious', readonly=True)

    is_current = fields.Boolean('Current', compute='_compute_is_current', readonly=True)

    device_line_ids = fields.One2many('res.device.line', compute='_compute_info', readonly=True)
    user_agent = fields.Char('User Agent', compute='_compute_info', search='_search_user_agent', readonly=True)
    ip_address = fields.Char('IP Address', compute='_compute_info', search='_search_ip_address', readonly=True)
    platform = fields.Char('Platform', compute='_compute_info', readonly=True)
    browser = fields.Char('Browser', compute='_compute_info', readonly=True)
    device_type = fields.Char('Type', compute='_compute_info', readonly=True)
    country = fields.Char('Country', compute='_compute_info', readonly=True)
    city = fields.Char('City', compute='_compute_info', readonly=True)

    def _compute_is_current(self):
        for device in self:
            device.is_current = request and request.session.sid.startswith(device.session_identifier)

    def _compute_info(self):
        device_map = {}
        for session_identifier, device_line_ids in self.env['res.device.line']._read_group(
            domain=[('session_identifier', 'in', self.mapped('session_identifier'))],
            groupby=['session_identifier'],
            aggregates=['id:recordset'],
        ):
            device_map[session_identifier] = device_line_ids.sorted('last_activity', reverse=True)

        for device in self:
            device_line_ids = device_map[device.session_identifier]
            device.device_line_ids = device_line_ids
            last_device_line_id = device_line_ids[0]  # because order is `last_activity desc`
            device.platform = last_device_line_id.platform
            device.browser = last_device_line_id.browser
            device.ip_address = last_device_line_id.ip_address
            device.device_type = last_device_line_id.device_type
            device.city = last_device_line_id.city
            device.country = last_device_line_id.country

    def _compute_display_name(self):
        for device in self:
            device.display_name = f"{device.platform.capitalize()} {device.browser.capitalize()}"

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == 'is_current' and request and request.session:
            return SQL("session_identifier = %s DESC", request.session.sid[:STORED_SESSION_BYTES])
        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    def _search_user_agent(self, operator, value):
        # Search in all device line and retrieve the session identifiers which used this User Agent
        data = self.env['res.device.line'].search_read([('user_agent', operator, value)], ['session_identifier'])
        session_identifiers = {dl['session_identifier'] for dl in data}
        return [('session_identifier', 'in', session_identifiers)]

    def _search_ip_address(self, operator, value):
        # Search in all device line and retrieve the session identifiers which used this IP address
        data = self.env['res.device.line'].search_read([('ip_address', operator, value)], ['session_identifier'])
        session_identifiers = {dl['session_identifier'] for dl in data}
        return [('session_identifier', 'in', session_identifiers)]

    @property
    def _query(self):
        return """
            SELECT
                MIN(DL.id) as id,
                DL.session_identifier as session_identifier,
                MIN(DL.user_id) as user_id,
                MIN(DL.first_activity) as first_activity,
                MAX(DL.last_activity) as last_activity,
                bool_or(DL.suspicious) as suspicious
            FROM
                res_device_line DL
            GROUP BY
                session_identifier
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE or REPLACE VIEW %s as (%s)
        """,
            SQL.identifier(self._table),
            SQL(self._query),
        ))

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
