# -*- coding: utf-8 -*-
import datetime
import time

from openerp import api, fields, models
from openerp import tools
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.bus.models.bus import TIMEOUT

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
        presence = self.search([('user_id', '=', self._uid)], limit=1)
        # compute last_presence timestamp
        last_presence = datetime.datetime.now() - datetime.timedelta(milliseconds=inactivity_period)
        values = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }
        # update the presence or a create a new one
        if not presence:  # create a new presence for the user
            values['user_id'] = self._uid
            values['last_presence'] = last_presence.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.create(values)
        else:  # update the last_presence if necessary, and write values
            if datetime.datetime.strptime(presence.last_presence, DEFAULT_SERVER_DATETIME_FORMAT) < last_presence:
                values['last_presence'] = last_presence.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            # Hide transaction serialization errors, which can be ignored, the presence update is not essential
            with tools.mute_logger('openerp.sql_db'):
                presence.write(values)
        # avoid TransactionRollbackError
        self.env.cr.commit() # TODO : check if still necessary
