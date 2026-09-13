import json
import logging
import typing
from datetime import UTC, datetime
from typing import Self

from odoo import api, fields, models, modules
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog
from odoo.service.transaction import PG_CONCURRENCY_ERRORS_TO_RETRY

if typing.TYPE_CHECKING:
    from .mail_message import MailMessage

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MailMessageSchedule(models.Model):
    _name = "mail.message.schedule"
    _description = "Scheduled Messages"
    _order = "scheduled_datetime DESC, id DESC"
    _rec_name = "mail_message_id"

    mail_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Message",
        index=True,
        required=True,
        ondelete="cascade",
    )
    notification_parameters = fields.Text(string="Notification Parameter")
    scheduled_datetime = fields.Datetime(
        string="Scheduled Send Date",
        index=True,
        required=True,
        help="Datetime at which notification should be sent.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        schedules = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(schedules),
            messages=schedules.mail_message_id.ids,
            dates=sorted(set(schedules.mapped("scheduled_datetime"))),
        )
        if schedules:
            self.env.ref("mail.ir_cron_send_scheduled_message")._add_triggers(
                set(schedules.mapped("scheduled_datetime"))
            )
        return schedules

    @api.model
    def _send_notifications_cron(self) -> None:
        batch_size = self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.scheduled_notification.batch.size", 500
        )
        messages_scheduled = self.env["mail.message.schedule"].search(
            [("scheduled_datetime", "<=", datetime.now(UTC))],
            limit=batch_size + 1,
            order="scheduled_datetime, id",
        )
        has_more = len(messages_scheduled) > batch_size
        messages_scheduled = messages_scheduled[:batch_size]
        _debug.pipeline(
            "cron_pass",
            due=len(messages_scheduled),
            batch_size=batch_size,
            more=has_more,
        )
        if not messages_scheduled:
            return
        _logger.info("Send %s scheduled messages", len(messages_scheduled))
        auto_commit = not modules.module.current_test
        for schedule in messages_scheduled:
            try:
                schedule._send_notifications()
                if auto_commit:
                    self.env.cr.commit()
            except Exception as error:
                if auto_commit:
                    self.env.cr.rollback()
                _debug.logic(
                    "send_failed",
                    schedule=schedule.id,
                    error=type(error).__name__,
                    retry=getattr(error, "sqlstate", None)
                    in PG_CONCURRENCY_ERRORS_TO_RETRY,
                )
                if getattr(error, "sqlstate", None) in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    _logger.warning(
                        "Transient DB error sending scheduled notification %s; "
                        "leaving it to retry on the next tick",
                        schedule.id,
                        exc_info=True,
                    )
                    continue
                _logger.warning(
                    "Sending of scheduled notification %s failed; dropping it",
                    schedule.id,
                    exc_info=True,
                )
                try:
                    schedule.unlink()
                except Exception:
                    _logger.exception(
                        "Could not drop the failed scheduled notification %s",
                        schedule.id,
                    )
                    if auto_commit:
                        self.env.cr.rollback()
                if auto_commit:
                    self.env.cr.commit()
        if has_more:
            self.env.ref("mail.ir_cron_send_scheduled_message")._trigger()

    def force_send(self) -> None:
        return self._send_notifications()

    def _send_notifications(self, default_notify_kwargs: dict | None = None) -> bool:
        for model, schedules in self._grouped_by_model().items():
            existing_ids = ()
            if model:
                res_ids = schedules.mapped("mail_message_id.res_id")
                existing_ids = set(self.env[model].browse(res_ids).exists()._ids)
            _debug.pipeline(
                "notifications_sent",
                model=model or None,
                schedules=len(schedules),
                existing=len(existing_ids),
            )

            for schedule in schedules:
                if model:
                    record = self.env[model].browse(schedule.mail_message_id.res_id)
                    if record.id not in existing_ids:
                        continue
                else:
                    record = self.env["mixin.mail.thread"]
                notify_kwargs = dict(default_notify_kwargs or {}, skip_existing=True)
                try:
                    schedule_notify_kwargs = (
                        schedule._deserialize_notification_parameters()
                    )
                except Exception:
                    _debug.logic(
                        "notification_parameters_invalid", schedule=schedule.id
                    )
                    _logger.warning(
                        "Invalid notification_parameters on mail.message.schedule %s; "
                        "using defaults.",
                        schedule.id,
                        exc_info=True,
                    )
                else:
                    schedule_notify_kwargs.pop("scheduled_date", None)
                    notify_kwargs.update(schedule_notify_kwargs)

                record._notify_thread(
                    schedule.mail_message_id, msg_vals=False, **notify_kwargs
                )

        self.unlink()
        return True

    @api.model
    def _serialize_notification_parameters(self, notify_kwargs: dict) -> str:
        serializable = dict(notify_kwargs)
        company = serializable.get("force_email_company")
        if company is not None and not isinstance(company, (bool, int)):
            serializable["force_email_company"] = company.id
        return json.dumps(serializable)

    def _deserialize_notification_parameters(self) -> dict:
        self.check_singleton()
        params = json.loads(self.notification_parameters or "{}")
        company_id = params.get("force_email_company")
        if company_id:
            params["force_email_company"] = self.env["res.company"].browse(company_id)
        return params

    @api.model
    def _send_message_notifications(
        self, messages: MailMessage, default_notify_kwargs: dict | None = None
    ) -> bool:
        messages_scheduled = self.search([("mail_message_id", "in", messages.ids)])
        if not messages_scheduled:
            return False

        messages_scheduled._send_notifications(
            default_notify_kwargs=default_notify_kwargs
        )
        return True

    @api.model
    def _update_message_scheduled_datetime(
        self, messages: MailMessage, new_datetime: datetime
    ) -> bool:
        messages_scheduled = self.search([("mail_message_id", "in", messages.ids)])
        if not messages_scheduled:
            return False

        _debug.lifecycle(
            "rescheduled", schedules=messages_scheduled.ids, scheduled=new_datetime
        )
        messages_scheduled.scheduled_datetime = new_datetime
        self.env.ref("mail.ir_cron_send_scheduled_message")._trigger(new_datetime)
        return True

    def _grouped_by_model(self) -> dict:
        grouped = {}
        for schedule in self:
            model = (
                schedule.mail_message_id.model
                if schedule.mail_message_id.model and schedule.mail_message_id.res_id
                else False
            )
            if model not in grouped:
                grouped[model] = schedule
            else:
                grouped[model] += schedule
        return grouped
