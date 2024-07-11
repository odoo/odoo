# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class MailNotification(models.Model):
    _inherit = "mail.notification"
    _populate_dependencies = ["res.partner", "mail.message"]

    def _populate(self, size):
        return super()._populate(size) + self._populate_threads(size, "res.partner")

    def _populate_threads(self, size, model_name):
        admin = self.env.ref("base.user_admin").partner_id
        random = populate.Random("mail.notification")
        partners = self.env["res.partner"].browse(self.env.registry.populated_models["res.partner"])
        threads = self.env[model_name].browse(self.env.registry.populated_models[model_name])
        threads_with_messages = threads.filtered(lambda thread: thread.message_ids)
        notifications = []
        big_done = 0
        max_possible = len(admin + partners)
        big = min(200, max_possible)
        _logger.info(
            "Preparing to populate mail.notification for %s threads with %s possible different recipients",
            len(threads_with_messages),
            max_possible,
        )
        for thread in random.sample(threads_with_messages, k={"small": 20, "medium": 150, "large": 300}[size]):
            for message in thread.message_ids:
                max_notifications = {"small": 10, "medium": 20, "large": 50}[size]
                number_notifications = big if big_done < 2 else random.randrange(max_notifications)
                if number_notifications >= big:
                    big_done += 1
                recipients = random.sample(admin + partners, k=min(number_notifications, max_possible))
                has_error = False
                for recipient in recipients:
                    notification_type = random.choices(["inbox", "email"], weights=[1, 10], k=1)[0]
                    force_error = not has_error and message.author_id == admin
                    notification_status = (
                        "sent"
                        if notification_type == "inbox"
                        else random.choices(
                            ["ready", "process", "pending", "sent", "bounce", "exception", "canceled"],
                            [1, 1, 1, 10, 10000 if force_error else 10, 10000 if force_error else 10, 2],
                            k=1,
                        )[0]
                    )
                    if notification_status in ["bounce", "exception"] and message.author_id == admin:
                        has_error = True
                    failure_type = (
                        False
                        if notification_status in ["ready", "process", "pending", "sent"]
                        else "mail_bounce"
                        if notification_status == "bounce"
                        else random.choice(
                            [
                                "unknown",
                                "mail_email_invalid",
                                "mail_email_missing",
                                "mail_from_invalid",
                                "mail_from_missing",
                                "mail_smtp",
                            ]
                        )
                    )
                    notifications.append(
                        {
                            "author_id": message.author_id.id,
                            "mail_message_id": message.id,
                            "res_partner_id": recipient.id,
                            "notification_type": notification_type,
                            "notification_status": notification_status,
                            "failure_type": failure_type,
                        }
                    )
        res = self.env["mail.notification"]
        batches = [notifications[i : i + 1000] for i in range(0, len(notifications), 1000)]
        count = 0
        for batch in batches:
            count += len(batch)
            _logger.info("Batch of mail.notification for %s: %s/%s", model_name, count, len(notifications))
            res += self.env["mail.notification"].create(batch)
        return res
