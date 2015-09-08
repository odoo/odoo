# -*- coding: utf-8 -*-
import datetime
import random
import time

from openerp import api, fields, models
from openerp import tools
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from openerp.addons.bus.models.bus import TIMEOUT

DISCONNECTION_TIMER = TIMEOUT + 5
AWAY_TIMER = 600 # 10 minutes


class BusPresence(models.Model):
    """ User Presence
        Its status is 'online', 'away' or 'offline'. This model should be a one2one, but is not
        attached to res_users to avoid database concurrence errors. Since the 'update' method is executed
        at each poll, if the user have multiple opened tabs, concurrence errors can happend, but are 'muted-logged'.
    """

    _name = 'bus.presence'
    _description = 'User Presence'

    _sql_constraints = [('bus_user_presence_unique', 'unique(user_id)', 'A user can only have one IM status.')]

    user_id = fields.Many2one('res.users', 'Users', required=True, index=True, ondelete='cascade')
    last_poll = fields.Datetime('Last Poll', default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime('Last Presence', default=lambda self: fields.Datetime.now())
    status = fields.Selection([('online', 'Online'), ('away', 'Away'), ('offline', 'Offline')], 'IM Status', default='offline')


    @api.model
    def update(self, user_presence=True):
        """ Register the given presence of the current user, and trigger a im_status change if necessary.
            The status will not be written or sent if not necessary.
            :param user_presence : True, if the user (self._uid) is still detected using its browser.
            :type user_presence : boolean
        """
        presence = self.search([('user_id', '=', self._uid)], limit=1)
        # set the default values
        send_notification = True
        values = {
            'last_poll': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'status': presence and presence.status or 'offline'
        }
        # update the user or a create a new one
        if not presence:  # create a new presence for the user
            values['status'] = 'online'
            values['user_id'] = self._uid
            self.create(values)
        else:  # write the user presence if necessary
            if user_presence:
                values['last_presence'] = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                values['status'] = 'online'
            else:
                threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
                if datetime.datetime.strptime(presence.last_presence, DEFAULT_SERVER_DATETIME_FORMAT) < threshold:
                    values['status'] = 'away'
            send_notification = presence.status != values['status']
            # write only if the last_poll is passed TIMEOUT, or if the status has changed
            delta = datetime.datetime.utcnow() - datetime.datetime.strptime(presence.last_poll, DEFAULT_SERVER_DATETIME_FORMAT)
            if delta > datetime.timedelta(seconds=TIMEOUT) or send_notification:
                # Hide transaction serialization errors, which can be ignored, the presence update is not essential
                with tools.mute_logger('openerp.sql_db'):
                    presence.write(values)
        # avoid TransactionRollbackError
        self.env.cr.commit() # TODO : check if still necessary
        # notify if the status has changed
        if send_notification: # TODO : add user_id to the channel tuple to allow using user_watch in controller presence
            self.env['bus.bus'].sendone((self._cr.dbname, 'bus.presence'), {'id': self._uid, 'im_status': values['status']})
        # gc : disconnect the users having a too old last_poll. 1 on 100 chance to do it.
        if random.random() < 0.01:
            self.check_users_disconnection()
        return True

    @api.model
    def check_users_disconnection(self):
        """ Disconnect the users having a too old last_poll """
        limit_date = (datetime.datetime.utcnow() - datetime.timedelta(0, DISCONNECTION_TIMER)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        presences = self.search([('last_poll', '<', limit_date), ('status', '!=', 'offline')])
        presences.write({'status': 'offline'})
        notifications = []
        for presence in presences:
            notifications.append([(self._cr.dbname, 'bus.presence'), {'id': presence.user_id.id, 'im_status': presence.status}])
        self.env['bus.bus'].sendmany(notifications)
