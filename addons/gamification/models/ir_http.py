# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        result = super()._dispatch(endpoint)
        cls._tag_session_for_interactions_log()
        return result

    @classmethod
    def _authenticate(cls, endpoint):
        result = super()._authenticate(endpoint)
        cls._tag_session_for_interactions_log(skip_log_record_update=True)
        return result

    @classmethod
    def _tag_session_for_interactions_log(cls, skip_log_record_update=False):
        """Add a timestamp to the session to throttle the interactions logging.

        For gamification goals purposes, it is sufficient to know whether users
        interacted with the application at least once between cron runs.
        This method avoids fetching user data from the db (as it is lazy-loaded)
        (and updating records) when it is not necessary. The timestamp value
        stored on the session is the moment after which it will be necessary to
        log user interaction again.

        This method will update the `no_interactions_log_until_timestamp`
        key to the session if necessary (not for public users or if the
        current time is before the existing value on the session).

        :param skip_log_record_update: Set `True` to also skip updating the
         user's `last_interaction_date`. It can for example be used
         when authenticating as the res.users.log record was just created
         with the correct value, we just need to tag the session.
        """
        if (
            not request.session.uid
            or time.time() < request.session.get("no_interactions_log_until_timestamp", 0)
            or not (user := request.env.user)
        ):
            return
        if not skip_log_record_update:
            user._update_last_interacted()
        if not user.last_interacted_date:
            return
        cron_interval_seconds = request.env['gamification.challenge']._get_cron_update_interval_or_default()
        request.session.no_interactions_log_until_timestamp = int(
            user.last_interacted_date.timestamp() + cron_interval_seconds / 3
        )
