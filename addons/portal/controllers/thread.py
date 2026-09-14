import logging

from werkzeug.exceptions import NotFound

from odoo.http import request

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.portal.utils import (
    get_portal_partner,
    is_thread_hash_pid_valid,
    resolve_message_thread,
)

_logger = logging.getLogger(__name__)


class PortalThreadController(ThreadController):
    def _prepare_message_data(self, post_data, *, thread, from_create=True, **kwargs):
        post_data = super()._prepare_message_data(
            post_data, thread=thread, from_create=from_create, **kwargs
        )
        if from_create and request.env.user._is_public():
            if partner := get_portal_partner(
                thread,
                kwargs.get("hash"),
                kwargs.get("pid"),
                kwargs.get("token"),
            ):
                post_data["author_id"] = partner.id
            elif is_thread_hash_pid_valid(
                thread, kwargs.get("hash"), kwargs.get("pid")
            ):
                # A signed recipient that no longer exists must not silently
                # become the public user (or a guest) through mail's fallback.
                _logger.debug(
                    "Rejecting portal post for missing signed recipient: model=%s id=%s pid=%s",
                    thread._name,
                    thread.id,
                    kwargs.get("pid"),
                )
                raise NotFound
        return post_data

    @classmethod
    def _can_edit_message(cls, message, hash=None, pid=None, token=None, **kwargs):
        if message.env.user._is_public():
            thread = resolve_message_thread(message)
            partner = get_portal_partner(thread, _hash=hash, pid=pid, token=token)
            if partner and message.author_id == partner:
                return True
        return super()._can_edit_message(
            message,
            hash=hash,
            pid=pid,
            token=token,
            **kwargs,
        )
