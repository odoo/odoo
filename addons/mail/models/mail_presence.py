# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, tools
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

UPDATE_PRESENCE_DELAY = 60
DISCONNECTION_TIMER = UPDATE_PRESENCE_DELAY + 5
AWAY_TIMER = 1800  # 30 minutes
PRESENCE_OUTDATED_TIMER = 12 * 60 * 60  # 12 hours


class MailPresence(models.Model):
    """User/Guest Presence
    Its status is 'online', 'away' or 'offline'. This model should be a one2one, but is not
    attached to res_users to avoid database concurrency errors.
    """

    _name = "mail.presence"
    _inherit = "bus.listener.mixin"
    _description = "User/Guest Presence"
    _log_access = False

    user_id = fields.Many2one("res.users", "Users", ondelete="cascade")
    guest_id = fields.Many2one("mail.guest", "Guest", ondelete="cascade")
    last_poll = fields.Datetime("Last Poll", default=lambda self: fields.Datetime.now())
    last_presence = fields.Datetime("Last Presence", default=lambda self: fields.Datetime.now())
    status = fields.Selection(
        [("online", "Online"), ("away", "Away"), ("offline", "Offline")],
        "IM Status",
        default="offline",
    )

    _guest_unique = models.UniqueIndex("(guest_id) WHERE guest_id IS NOT NULL")
    _user_unique = models.UniqueIndex("(user_id) WHERE user_id IS NOT NULL")

    _partner_or_guest_exists = models.Constraint(
        "CHECK((user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL))",
        "A mail presence must have a user or a guest.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        presences = super().create(vals_list)
        presences._send_presence()
        return presences

    def write(self, vals):
        status_by_presence = {presence: presence.status for presence in self}
        result = super().write(vals)
        updated = self.filtered(lambda p: status_by_presence[p] != p.status)
        updated._send_presence()
        return result

    def unlink(self):
        self._send_presence("offline")
        return super().unlink()

    @api.model
    def _try_update_presence(self, user_or_guest, inactivity_period=0):
        """Updates the last_poll and last_presence of the current user
        :param inactivity_period: duration in milliseconds
        """
        # This method is called in method _poll() and cursor is closed right
        # after; see bus/controllers/main.py.
        try:
            # Hide transaction serialization errors, which can be ignored, the presence update is not essential
            # The errors are supposed from presence.write(...) call only
            with tools.mute_logger("odoo.sql_db"):
                self._update_presence(user_or_guest, inactivity_period)
                # commit on success
                self.env.cr.commit()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # ignore concurrency error
            return self.env.cr.rollback()

    @api.model
    def _update_presence(self, user_or_guest, inactivity_period=0):
        values = {
            "last_poll": fields.Datetime.now(),
            "last_presence": fields.Datetime.now() - timedelta(milliseconds=inactivity_period),
            "status": "away" if inactivity_period > AWAY_TIMER * 1000 else "online",
        }
        # sudo: res.users/mail.guest can update presence of accessible user/guest
        user_or_guest_sudo = user_or_guest.sudo()
        if presence := user_or_guest_sudo.presence_ids:
            presence.write(values)
        else:
            values["guest_id" if user_or_guest._name == "mail.guest" else "user_id"] = user_or_guest.id
            # sudo: res.users/mail.guest can update presence of accessible user/guest
            self.env["mail.presence"].sudo().create(values)

    def _send_presence(self, im_status=None, bus_target=None):
        """Send notification related to bus presence update.

        :param im_status: 'online', 'away' or 'offline'
        """
        for presence in self:
            target = bus_target or presence.guest_id or presence.user_id.partner_id
            target._bus_send(
                "bus.bus/im_status_updated",
                {
                    "presence_status": im_status or presence.status,
                    "im_status": target.im_status,
                    "guest_id": presence.guest_id.id,
                    "partner_id": presence.user_id.partner_id.id,
                },
                subchannel="presence" if not bus_target else None,
            )

    @api.autovacuum
    def _gc_bus_presence(self):
        self.search(
            [("last_poll", "<", fields.Datetime.now() - timedelta(seconds=PRESENCE_OUTDATED_TIMER))]
        ).unlink()
