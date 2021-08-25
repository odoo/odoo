# -*- coding: utf-8 -*-
import datetime
import time

from psycopg2 import OperationalError

from odoo import api, fields, models
from odoo import tools
from odoo.addons.bus.models.bus import TIMEOUT
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

DISCONNECTION_TIMER = TIMEOUT + 5
AWAY_TIMER = 1800  # 30 minutes


class BusPresence(models.Model):
    """ User Presence
        Its status is 'online', 'away' or 'offline'. This model should be a one2one, but is not
        attached to res_users to avoid database concurrence errors. Since the 'update' method is executed
        at each poll, if the user have multiple opened tabs, concurrence errors can happend, but are 'muted-logged'.
    """

    _name = 'bus.presence'
    _description = 'User Presence'
    _log_access = False

    _sql_constraints = [('bus_user_presence_unique', 'unique(user_id)', 'A user can only have one IM status.')]

    user_id = fields.Many2one('res.users', 'Users', required=True, index=True, ondelete='cascade')
    last_poll = fields.Datetime('Last Poll', default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime('Last Presence', default=lambda self: fields.Datetime.now())
    status = fields.Selection([('online', 'Online'), ('away', 'Away'), ('offline', 'Offline')], 'IM Status', default='offline')

    @api.model
    def update(self, inactivity_period):
        """ Updates the last_poll and last_presence of the current user
            :param inactivity_period: duration in milliseconds
        """
        # This method is called in method _poll() and cursor is closed right
        # after; see bus/controllers/main.py.
        try:
            self._update(inactivity_period)
            # commit on success
            self.env.cr.commit()
        except OperationalError as e:
            if e.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                # ignore concurrency error
                return self.env.cr.rollback()
            raise

    @api.model
    def _update(self, inactivity_period):
        presence = self.search([('user_id', '=', self._uid)], limit=1)
        # compute last_presence timestamp
        last_presence = datetime.datetime.now() - datetime.timedelta(milliseconds=inactivity_period)
        values = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
        # update the presence or a create a new one
        if not presence:  # create a new presence for the user
            values['user_id'] = self._uid
            values['last_presence'] = last_presence
            self.create(values)
        else:  # update the last_presence if necessary, and write values
            if presence.last_presence < last_presence:
                values['last_presence'] = last_presence
            # Hide transaction serialization errors, which can be ignored, the presence update is not essential
            with tools.mute_logger('odoo.sql_db'):
                presence.write(values)
                presence.flush()
