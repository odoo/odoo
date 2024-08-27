# -*- coding: utf-8 -*-
import time

from datetime import datetime, timedelta
from psycopg2 import OperationalError

from odoo import api, fields, models
from odoo import tools
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

UPDATE_PRESENCE_DELAY = 60
DISCONNECTION_TIMER = UPDATE_PRESENCE_DELAY + 5
AWAY_TIMER = 1800  # 30 minutes
PRESENCE_OUTDATED_TIMER = 12 * 60 * 60  # 12 hours


class BusPresence(models.Model):
    """ User Presence
        Its status is 'online', 'away' or 'offline'. This model should be a one2one, but is not
        attached to res_users to avoid database concurrence errors. Since the 'update_presence' method is executed
        at each poll, if the user have multiple opened tabs, concurrence errors can happend, but are 'muted-logged'.
    """

    _name = 'bus.presence'
    _description = 'User Presence'
    _log_access = False

    user_id = fields.Many2one('res.users', 'Users', ondelete='cascade')
    last_poll = fields.Datetime('Last Poll', default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime('Last Presence', default=lambda self: fields.Datetime.now())
    status = fields.Selection([('online', 'Online'), ('away', 'Away'), ('offline', 'Offline')], 'IM Status', default='offline')

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS bus_presence_user_unique ON %s (user_id) WHERE user_id IS NOT NULL" % self._table)

    def create(self, values):
        presences = super().create(values)
        presences._invalidate_im_status()
        presences._send_presence()
        return presences

    def write(self, values):
        status_by_user = {presence._get_identity_field_name(): presence.status for presence in self}
        result = super().write(values)
        updated = self.filtered(lambda p: status_by_user[p._get_identity_field_name()] != p.status)
        updated._invalidate_im_status()
        updated._send_presence()
        return result

    def unlink(self):
        self._send_presence("offline")
        return super().unlink()

    @api.model
    def update_presence(self, inactivity_period, identity_field, identity_value):
        """ Updates the last_poll and last_presence of the current user
            :param inactivity_period: duration in milliseconds
        """
        # This method is called in method _poll() and cursor is closed right
        # after; see bus/controllers/main.py.
        try:
            # Hide transaction serialization errors, which can be ignored, the presence update is not essential
            # The errors are supposed from presence.write(...) call only
            with tools.mute_logger('odoo.sql_db'):
                self._update_presence(inactivity_period=inactivity_period, identity_field=identity_field, identity_value=identity_value)
                # commit on success
                self.env.cr.commit()
        except OperationalError as e:
            if e.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                # ignore concurrency error
                return self.env.cr.rollback()
            raise

    def _get_bus_target(self):
        self.ensure_one()
        return self.user_id.partner_id if self.user_id else None

    def _get_identity_field_name(self):
        self.ensure_one()
        return "user_id" if self.user_id else None

    def _get_identity_data(self):
        self.ensure_one()
        return {"partner_id": self.user_id.partner_id.id} if self.user_id else None

    @api.model
    def _update_presence(self, inactivity_period, identity_field, identity_value):
        presence = self.search([(identity_field, "=", identity_value)])
        values = {
            "last_poll": time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            "last_presence": datetime.now() - timedelta(milliseconds=inactivity_period),
            "status": "away" if inactivity_period > AWAY_TIMER * 1000 else "online",
        }
        if not presence:
            values[identity_field] = identity_value
            presence = self.create(values)
        else:
            presence.write(values)

    def _invalidate_im_status(self):
        self.user_id.invalidate_recordset(["im_status"])
        self.user_id.partner_id.invalidate_recordset(["im_status"])

    def _send_presence(self, im_status=None, bus_target=None):
        """Send notification related to bus presence update.

        :param im_status: 'online', 'away' or 'offline'
        """
        notifications = []
        for presence in self:
            identity_data = presence._get_identity_data()
            target = presence._get_bus_target()
            target = bus_target or (target and (target, "presence"))
            if identity_data and target:
                notifications.append(
                    (
                        target,
                        "bus.bus/im_status_updated",
                        {"im_status": im_status or presence.status, **identity_data},
                    )
                )
        self.env["bus.bus"]._sendmany(notifications)

    @api.autovacuum
    def _gc_bus_presence(self):
        self.search(
            [("last_poll", "<", datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER))]
        ).unlink()
