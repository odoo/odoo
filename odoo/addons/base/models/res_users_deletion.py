import logging

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ResUsersDeletion(models.Model):
    _name = "res.users.deletion"
    _description = "Users Deletion Request"
    _rec_name = "user_id"

    user_id = fields.Many2one(
        comodel_name="res.users",
        ondelete="set null",
    )
    user_id_int = fields.Integer(
        string="User Id",
        compute="_compute_user_id_int",
        store=True,
    )
    state = fields.Selection(
        selection=[("todo", "To Do"), ("done", "Done"), ("fail", "Failed")],
        default="todo",
        required=True,
        help="Deletion request lifecycle: 'todo' when queued, 'done' once the "
        "user is deleted, 'fail' if deletion was attempted but could not "
        "complete (the user is then archived instead).",
    )

    @api.depends("user_id")
    def _compute_user_id_int(self) -> None:
        for user_deletion in self:
            if user_deletion.user_id:
                user_deletion.user_id_int = user_deletion.user_id.id

    @api.model
    def _get_domain_deletion_due(self) -> list:
        return [("state", "=", "todo")]

    @api.model
    def _gc_portal_users(self, batch_size: int = 50) -> None:
        delete_requests = self.search(self._get_domain_deletion_due())

        done_requests = delete_requests.filtered(lambda request: not request.user_id)
        done_requests.state = "done"

        todo_requests = delete_requests - done_requests
        _debug.pipeline(
            "gc_portal_users",
            requests=len(delete_requests),
            already_gone=len(done_requests),
            todo=len(todo_requests),
            batch_size=batch_size,
        )
        commit_progress = self.env["ir.cron"]._commit_progress
        commit_progress(len(done_requests), remaining=len(todo_requests))

        for delete_request in todo_requests[:batch_size]:
            delete_request = delete_request.try_lock_for_update().filtered(
                lambda d: d.state == "todo"
            )
            if not delete_request:
                _debug.logic("deletion_request_skipped", reason="locked_or_done")
                continue
            user = delete_request.user_id
            user_name = user.name
            partner = user.partner_id
            requester_name = delete_request.create_uid.name

            try:
                user.unlink()
                _logger.info(
                    "User #%i %r, deleted. Original request from %r.",
                    user.id,
                    user_name,
                    requester_name,
                )
                delete_request.state = "done"
                _debug.lifecycle(
                    "user_deleted", request=delete_request.id, user=user.id
                )
                commit_progress(1)
            except Exception as e:
                self.env.cr.rollback()
                _logger.error(
                    "User #%i %r could not be deleted. Original request from %r. Related error: %s",
                    user.id,
                    user_name,
                    requester_name,
                    e,
                )
                _debug.lifecycle(
                    "user_deletion_failed",
                    request=delete_request.id,
                    user=user.id,
                    error=type(e).__name__,
                )
                delete_request.state = "fail"
                if commit_progress(1):
                    continue
                break

            try:
                if not partner.exists():
                    _debug.logic(
                        "partner_deletion_skipped",
                        request=delete_request.id,
                        reason="already_gone",
                    )
                    if not commit_progress():
                        break
                    continue
                partner.unlink()
                _logger.info(
                    "Partner #%i %r, deleted. Original request from %r.",
                    partner.id,
                    user_name,
                    requester_name,
                )
                _debug.lifecycle(
                    "partner_deleted", request=delete_request.id, partner=partner.id
                )
                if not commit_progress():
                    break
            except Exception as e:
                self.env.cr.rollback()
                _logger.warning(
                    "Partner #%i %r could not be deleted. Original request from %r. Related error: %s",
                    partner.id,
                    user_name,
                    requester_name,
                    e,
                )
                _debug.lifecycle(
                    "partner_deletion_failed",
                    request=delete_request.id,
                    partner=partner.id,
                    error=type(e).__name__,
                )
                if not commit_progress():
                    break
