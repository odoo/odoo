# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussChannelLastInterestUpdate(models.Model):
    """Append-only queue of pending ``discuss.channel.last_interest_dt`` updates.

    Posting a message records the channel's new "last interest" as a new row here. An INSERT
    never serializes against parallel posters (unlike updating the hot channel row inside the
    request transaction), so posts no longer crash with a Postgres serialization error on busy
    or slow (e.g. AI flow) channels. The value is synced onto
    ``discuss.channel.last_interest_dt`` after commit by ``_sync_last_interest_dt`` (and by the
    ``ir_cron_discuss_channel_sync_last_interest_dt`` cron as a durable fallback), so reads and
    sorting keep using the indexed channel column.
    """

    _name = "discuss.channel.last.interest.update"
    _description = "Pending Channel Last Interest Update"
    _log_access = False

    channel_id = fields.Many2one(
        "discuss.channel", required=True, ondelete="cascade", index=True
    )
    last_interest_dt = fields.Datetime(required=True)
