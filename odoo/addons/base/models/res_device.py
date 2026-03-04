# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, tools
from odoo.http import request
from odoo.http.session import (
    STORED_SESSION_BYTES,
    get_session_max_inactivity,
    logout,
    session_store,
    update_device,
)
from odoo.tools import SQL
from odoo.tools._vendor.useragents import UserAgent
from odoo.tools.translate import _

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
        device = update_device(request.session, request)
        if not device:
            return

        user_id = request.session.uid
        session_identifier = request.session.sid[:STORED_SESSION_BYTES]

        if self.env.cr.readonly:
            self.env.cr.rollback()

        with self.env.registry.cursor() as cr:
            info = {
                'session_identifier': session_identifier,
                'user_id': user_id,
                'ip_address': device['ip_address'],
                'user_agent': device['user_agent'][:1024],  # Truncate very long user-agent
                'country': device.get('country'),  # TODO (v20): remove backward compatibility by forcing the key
                'city': device.get('city'),  # TODO (v20): remove backward compatibility by forcing the key
                'first_activity': datetime.fromtimestamp(device['first_activity']),
                'last_activity': datetime.fromtimestamp(device['last_activity']),
                'revoked': False,
            }
            cr.execute(SQL("""
                INSERT INTO res_device_log (session_identifier, user_id, ip_address, user_agent, country, city, first_activity, last_activity, revoked)
                VALUES (%(session_identifier)s, %(user_id)s, %(ip_address)s, %(user_agent)s, %(country)s, %(city)s, %(first_activity)s, %(last_activity)s, %(revoked)s)
            """, **info))
            _logger.info('User %(user_id)d inserts device log: %(session_identifier)s - %(ip_address)s - %(user_agent)s', info)
            session_store().save(request.session)

    @api.autovacuum
    def _gc_device_log(self):
        # Soft GC:
        # Keep the last device log even if the session file
        # no longer exists on the filesystem
        query = SQL("""
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

        # Hard GC:
        # Delete device logs if the last activity has been exceeded by a defined
        # number of days (ensure the session file no longer exists on the filesystem)
        if retention_days := self.env['ir.config_parameter'].get_int('base.res_device_log_retention_days'):
            max_last_activity = self.env.cr.now() - timedelta(days=retention_days)
            query = SQL(
                '%s OR (log1.revoked IS TRUE AND log1.last_activity < %s)',
                query, max_last_activity,
            )

        self.env.cr.execute(query)
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
            revoked_session_identifiers = session_store().get_missing_session_identifiers(
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
        # Deduplicate logs to keep only the most recent one for each device.
        # - `first_activity` is propagated, so it will be correct with the most
        #   recent log.
        # - `id` is not aggregated, this allows the ORM to use relational fields
        #   with this model and use the index of `id`.
        return """
            SELECT
                L1.id,
                L1.session_identifier,
                L1.user_id,
                L1.ip_address,
                L1.user_agent,
                L1.country,
                L1.city,
                L1.first_activity,
                L1.last_activity,
                L1.revoked
            FROM res_device_log L1
            WHERE
                L1.revoked IS NOT TRUE
                AND NOT ( EXISTS (
                    SELECT 1
                    FROM
                        res_device_log L2
                    WHERE
                        L2.user_id = L1.user_id
                        AND L2.session_identifier = L1.session_identifier
                        AND L2.ip_address = L1.ip_address
                        AND L2.user_agent = L1.user_agent
                        AND L2.id > L1.id
                        AND L2.revoked IS NOT TRUE
                ))
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
    first_activity = fields.Datetime('First Activity', compute='_compute_session_info', readonly=True)

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
            session.first_activity = min(device_ids.mapped('first_activity'))

    def _compute_display_name(self):
        for session in self:
            session.display_name = f'{session.platform.capitalize()} {session.browser.capitalize()}'

    def _order_field_to_sql(self, table, field_expr, direction, nulls):
        if field_expr == 'is_current' and request and request.session:
            return SQL('session_identifier = %s DESC', request.session.sid[:STORED_SESSION_BYTES])
        return super()._order_field_to_sql(table, field_expr, direction, nulls)

    @property
    def _query(self):
        # A `res.session` record is represented with the most recent device for
        # a given `session_identifier`.
        # - The max of `last_activity` will be always the `last_activity` of the
        #   most recent device, but the min of `first_activity` must be retrieve
        #   from all devices in the session.
        # - `id` is not aggregated, we can use the `id` of the underlying table
        #   as an index (`res.device` --> `res.device.log`).
        # - The aggregated fields will be computed (this is because the most
        #   recent log may not correspond to the current device, the latter to
        #   be used for a good user experience).
        return """
            SELECT
                D1.id,
                D1.session_identifier,
                D1.user_id,
                D1.last_activity,
                D1.revoked
            FROM res_device D1
            WHERE
                NOT ( EXISTS (
                    SELECT 1
                    FROM
                        res_device D2
                    WHERE
                        D2.user_id = D1.user_id
                        AND D2.session_identifier = D1.session_identifier
                        AND D2.id > D1.id
                ))
        """

    @check_identity
    def revoke(self):
        return self._revoke()

    def _revoke(self):
        ResDeviceLog = self.env['res.device.log']
        session_identifiers = list(set(self.mapped('session_identifier')))
        session_store().delete_from_identifiers(session_identifiers)
        revoked_devices = ResDeviceLog.sudo().search([
            ('session_identifier', 'in', session_identifiers),
            ('revoked', '=', False),
        ])
        revoked_devices.write({'revoked': True})
        _logger.info('User %d revokes devices (%s)', self.env.uid, ', '.join(session_identifiers))

        must_logout = bool(self.filtered('is_current'))
        if must_logout:
            logout(request.session)
