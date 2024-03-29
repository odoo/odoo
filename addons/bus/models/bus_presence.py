# -*- coding: utf-8 -*-
import datetime
import time

from psycopg2 import OperationalError

from odoo import api, fields, models
from odoo import tools
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

UPDATE_PRESENCE_DELAY = 60
DISCONNECTION_TIMER = UPDATE_PRESENCE_DELAY + 5
AWAY_TIMER = 1800  # 30 minutes


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

    @api.model
    def _update_presence(self, inactivity_period, identity_field, identity_value):
        presence = self.search([(identity_field, '=', identity_value)], limit=1)
        # compute last_presence timestamp
        last_presence = datetime.datetime.now() - datetime.timedelta(milliseconds=inactivity_period)
        values = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
        # update the presence or a create a new one
        if not presence:  # create a new presence for the user
            values[identity_field] = identity_value
            values['last_presence'] = last_presence
            self.create(values)
        else:  # update the last_presence if necessary, and write values
            if presence.last_presence < last_presence:
                values['last_presence'] = last_presence
            presence.write(values)

    @api.autovacuum
    def _gc_bus_presence(self):
        self.search([('user_id.active', '=', False)]).unlink()
