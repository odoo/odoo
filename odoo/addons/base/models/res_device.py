# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext
from datetime import datetime, timedelta
import logging

from odoo import api, fields, models, tools
from odoo.http import get_session_max_inactivity, request, root, STORED_SESSION_BYTES
from odoo.tools import SQL
from odoo.tools.translate import _
from odoo.tools._vendor.useragents import UserAgent
from .res_users import check_identity

_logger = logging.getLogger(__name__)


class ResDeviceLog(models.Model):
    _name = 'res.device.log'
    _description = 'Device Log'
    _rec_names_search = ['ip_address', 'user_agent']

    # Fields that identify a session
    session_identifier = fields.Char('Session Identifier', required=True, index='btree')
    user_id = fields.Integer(string='User', required=True, index='btree')
    # Note:
    # `user_id` is an Integer to keep a reference to the user even when the user
    # is deleted. This avoids having a foreign key.
    # Fields that identify a device for a given session (comes from the HTTP request information
    ip_address = fields.Char('IP Address', required=True)
    user_agent = fields.Char('User Agent', required=True)
    # Store the country and city as this data may change over time for the same IP address
    country = fields.Char('Country')
    city = fields.Char('City')
    # Fields that represent the device's activity
    first_activity = fields.Datetime('First Activity', required=True)
    last_activity = fields.Datetime('Last Activity', required=True, index='btree')
    # Field that determine the "status" of the session/device on disk
    revoked = fields.Boolean('Revoked',
                            help="""If True, the session file corresponding to this device
                                    no longer exists on the filesystem.""")

    _composite_idx = models.Index('(session_identifier, ip_address, user_agent, id) WHERE revoked IS NOT TRUE')
    _revoked_idx = models.Index('(revoked) WHERE revoked IS NOT TRUE')

    @api.model
    def _update_device(self, request):
        """
            Must be called when we want to update the device for the current request.
            Passage through this method must leave a "trace" in the session.

            :param request: Request or WebsocketRequest object
        """
        device = request.session.update_device(request)
        if not device:
            return

        user_id = request.session.uid
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]

        if self.env.cr.readonly:
            self.env.cr.rollback()
            cursor = self.env.registry.cursor(readonly=False)
        else:
            cursor = nullcontext(self.env.cr)
        with cursor as cr:
            cr.execute(SQL("""
                INSERT INTO res_device_log (session_identifier, user_id, ip_address, user_agent, country, city, first_activity, last_activity, revoked)
                VALUES (%(session_identifier)s, %(user_id)s, %(ip_address)s, %(user_agent)s, %(country)s, %(city)s, %(first_activity)s, %(last_activity)s, %(revoked)s)
            """,
                session_identifier=session_identifier,
                user_id=user_id,
                ip_address=device['ip_address'],
                user_agent=device['user_agent'][:1024],  # Truncate very long user-agent
                country=device.get('country'),  # TODO (v20): remove backward compatibility by forcing the key
                city=device.get('city'),  # TODO (v20): remove backward compatibility by forcing the key
                first_activity=datetime.fromtimestamp(device['first_activity']),
                last_activity=datetime.fromtimestamp(device['last_activity']),
                revoked=False,
            ))
        _logger.info('User %d inserts device log (%s)', user_id, session_identifier)

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
                    AND log1.ip_address = log2.ip_address
                    AND log1.user_agent = log2.user_agent
                    AND log1.last_activity < log2.last_activity
            )
        """)
        _logger.info('GC device logs delete %d entries', self.env.cr.rowcount)

    @api.autovacuum
    def __update_revoked(self):
        """
            Set the field ``revoked`` to ``True`` for ``res.device.log``
            for which the session file no longer exists on the filesystem.
        """
        batch_size = 100_000
        offset = 0

        while True:
            candidate_device_log_ids = self.env['res.device.log'].search_fetch(
                [
                    ('revoked', '=', False),
                    ('last_activity', '<', datetime.now() - timedelta(seconds=get_session_max_inactivity(self.env))),
                ],
                ['session_identifier'],
                order='id',
                limit=batch_size,
                offset=offset,
            )
            if not candidate_device_log_ids:
                break
            offset += batch_size
            revoked_session_identifiers = root.session_store.get_missing_session_identifiers(
                set(candidate_device_log_ids.mapped('session_identifier')),
            )
            if not revoked_session_identifiers:
                continue
            to_revoke = candidate_device_log_ids.filtered(
                lambda candidate: candidate.session_identifier in revoked_session_identifiers
            )
            to_revoke.write({'revoked': True})
            self.env.cr.commit()
            offset -= len(to_revoke)


class ResDevice(models.Model):
    _name = 'res.device'
    _description = 'Device'
    _auto = False
    _order = 'last_activity desc'

    session_identifier = fields.Char('Session identifier', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    ip_address = fields.Char('IP Address', readonly=True)
    country = fields.Char('Country', readonly=True)
    city = fields.Char('City', readonly=True)
    user_agent = fields.Char('User Agent', readonly=True)
    first_activity = fields.Datetime('First Activity', readonly=True)
    last_activity = fields.Datetime('Last Activity', readonly=True)
    revoked = fields.Boolean('Revoked', readonly=True)

    platform = fields.Char('Platform', compute='_compute_device_info', readonly=True)
    browser = fields.Char('Browser', compute='_compute_device_info', readonly=True)
    browser_version = fields.Char('Browser Version', compute='_compute_device_info', readonly=True)
    browser_language = fields.Char('Browser Language', compute='_compute_device_info', readonly=True)
    device_type = fields.Char('Type', compute='_compute_device_info', readonly=True)

    is_current = fields.Boolean('Current', compute='_compute_is_current', readonly=True)

    __user_agent_parser = UserAgent._parser
    __mobile_platform = ('android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone', 'webos')

    def _compute_is_current(self):
        if not request or not hasattr(request, 'httprequest'):
            self.is_current = False
            return
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.user_agent.string
        for device in self:
            device.is_current = \
                device.session_identifier == session_identifier and \
                device.ip_address == ip_address and \
                device.user_agent == user_agent

    def _compute_device_info(self):
        for device in self:
            platform, browser, browser_version, browser_language = self.__user_agent_parser(device.user_agent)
            device.platform = platform or _('Unknown')
            device.browser = browser or _('Unknown')
            device.browser_version = browser_version or _('Unknown')
            device.browser_language = browser_language or _('Unknown')
            device.device_type = 'mobile' if device.platform in self.__mobile_platform else 'computer'

    @property
    def _query(self):
        return """
            SELECT
                MAX(L.id) as id,
                L.session_identifier as session_identifier,
                MIN(L.user_id) as user_id,
                L.ip_address as ip_address,
                L.user_agent as user_agent,
                MAX(L.country) as country,
                MAX(L.city) as city,
                MIN(L.first_activity) as first_activity,
                MAX(L.last_activity) as last_activity,
                bool_and(L.revoked) as revoked
            FROM
                res_device_log L
            WHERE
                L.revoked IS NOT TRUE
            GROUP BY
                session_identifier,
                ip_address,
                user_agent
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('CREATE OR REPLACE VIEW %s AS (%s)' % (self._table, self._query))


class ResSession(models.Model):
    _name = 'res.session'
    _inherit = ['res.device']
    _description = 'Session'
    _auto = False
    _order = 'last_activity desc'

    device_ids = fields.One2many('res.device', compute='_compute_session_info', readonly=True)
    ip_address = fields.Char('IP Address', compute='_compute_session_info', readonly=True)
    user_agent = fields.Char('User Agent', compute='_compute_session_info', readonly=True)
    country = fields.Char('Country', compute='_compute_session_info', readonly=True)
    city = fields.Char('City', compute='_compute_session_info', readonly=True)

    is_current = fields.Boolean('Current', compute='_compute_is_current', readonly=True)

    def _compute_is_current(self):
        if not request:
            self.is_current = False
            return
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]
        for session in self:
            session.is_current = session.session_identifier == session_identifier

    def _compute_session_info(self):
        session_map = {}
        for session_identifier, device_line_ids in self.env['res.device']._read_group(
            domain=[('session_identifier', 'in', self.mapped('session_identifier'))],
            groupby=['session_identifier'],
            aggregates=['id:recordset'],
        ):
            session_map[session_identifier] = device_line_ids.sorted('last_activity', reverse=True)

        for session in self:
            device_ids = session_map[session.session_identifier]
            session.device_ids = device_ids
            if session.is_current:
                # The user will see the information for the device he is
                # currently using, even if there are more recent logs for
                # another device.
                current_device_id = device_ids.filtered('is_current')
            else:
                current_device_id = device_ids[0]  # because order is `last_activity desc`
            session.ip_address = current_device_id.ip_address
            session.user_agent = current_device_id.user_agent
            session.country = current_device_id.country
            session.city = current_device_id.city

    def _compute_display_name(self):
        for session in self:
            session.display_name = f'{session.platform.capitalize()} {session.browser.capitalize()}'

    def _order_field_to_sql(self, table, field_expr, direction, nulls):
        if field_expr == 'is_current' and request and request.session:
            return SQL('session_identifier = %s DESC', request.session.sid[:STORED_SESSION_BYTES])
        return super()._order_field_to_sql(table, field_expr, direction, nulls)

    @property
    def _query(self):
        return """
            SELECT
                MAX(D.id) as id,
                D.session_identifier as session_identifier,
                MIN(D.user_id) as user_id,
                MIN(D.first_activity) as first_activity,
                MAX(D.last_activity) as last_activity,
                bool_and(D.revoked) as revoked
            FROM
                res_device D
            GROUP BY
                session_identifier
        """

    @check_identity
    def revoke(self):
        return self._revoke()

    def _revoke(self):
        ResDeviceLog = self.env['res.device.log']
        session_identifiers = list(set(self.mapped('session_identifier')))
        root.session_store.delete_from_identifiers(session_identifiers)
        revoked_devices = ResDeviceLog.sudo().search([
            ('session_identifier', 'in', session_identifiers),
            ('revoked', '=', False),
        ])
        revoked_devices.write({'revoked': True})
        _logger.info('User %d revokes devices (%s)', self.env.uid, ', '.join(session_identifiers))

        must_logout = bool(self.filtered('is_current'))
        if must_logout:
            request.session.logout()
