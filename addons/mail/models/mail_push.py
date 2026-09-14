import logging
import typing
from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.web_push import (
    DeviceUnreachableError,
    PushEndpointUnresolvableError,
    get_push_session,
    push_to_end_point,
)

if typing.TYPE_CHECKING:
    from .mail_push_device import MailPushDevice

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

PUSH_ENDPOINT_RETRY_DAYS = 3
PUSH_ENDPOINT_RETRY_DELAY = timedelta(minutes=15)


class MailPush(models.Model):
    _name = "mail.push"
    _description = "Push Notifications"

    mail_push_device_id: MailPushDevice = fields.Many2one(
        comodel_name="mail.push.device",
        string="devices",
        required=True,
        ondelete="cascade",
    )
    payload = fields.Text()
    retry_after = fields.Datetime(
        index=True,
        help="Set when the device endpoint could not be resolved; the "
        "notification is skipped by the sending cron until this date so a "
        "single unreachable endpoint cannot starve the rest of the queue.",
    )

    @api.model
    def _get_domain_due(self) -> Domain:
        return Domain("retry_after", "=", False) | Domain(
            "retry_after", "<=", fields.Datetime.now()
        )

    @api.model
    def _push_notification_to_endpoint(self, batch_size: int = 50) -> None:
        due_domain = self._get_domain_due()
        web_push_notifications_sudo = self.sudo().search_fetch(
            due_domain, ["mail_push_device_id", "payload"], limit=batch_size
        )
        if not web_push_notifications_sudo:
            return

        ir_parameter_sudo = self.env["ir.config_parameter"].sudo()
        vapid_private_key = self.env["credential.credential"]._get_system_secret(
            "mail.web_push_vapid_private_key"
        )
        vapid_public_key = ir_parameter_sudo.get_param("mail.web_push_vapid_public_key")
        if not vapid_private_key or not vapid_public_key:
            _debug.logic("push_cron_skipped", reason="no_vapid_keys")
            return

        session = get_push_session(self.env)
        devices_to_unlink = set()
        retry_delay_by_notif_id = {}

        base_url = self.get_base_url()
        devices = web_push_notifications_sudo.mail_push_device_id.grouped("id")
        for web_push_notification_sudo in web_push_notifications_sudo:
            device = devices.get(web_push_notification_sudo.mail_push_device_id.id)
            if device.id in devices_to_unlink:
                continue
            try:
                push_to_end_point(
                    base_url=base_url,
                    device={
                        "id": device.id,
                        "endpoint": device.endpoint,
                        "keys": device.keys,
                    },
                    payload=web_push_notification_sudo.payload,
                    vapid_private_key=vapid_private_key,
                    vapid_public_key=vapid_public_key,
                    session=session,
                )
            except DeviceUnreachableError:
                devices_to_unlink.add(device.id)
            except PushEndpointUnresolvableError as error:
                retry_delay_by_notif_id[web_push_notification_sudo.id] = min(
                    error.retry_after or PUSH_ENDPOINT_RETRY_DELAY,
                    timedelta(days=PUSH_ENDPOINT_RETRY_DAYS),
                )
                _logger.info(
                    "Push endpoint temporarily unavailable (%s), keeping device %s",
                    error,
                    device.id,
                )
            except Exception as e:
                _logger.error("An error occurred while trying to send web push: %s", e)

        now = fields.Datetime.now()
        retry_cutoff = now - timedelta(days=PUSH_ENDPOINT_RETRY_DAYS)
        notifs_to_keep = web_push_notifications_sudo.filtered(
            lambda n: (
                n.id in retry_delay_by_notif_id
                and n.create_date
                and n.create_date > retry_cutoff
            )
        )
        _debug.pipeline(
            "push_cron_pass",
            batch_size=batch_size,
            notifications=len(web_push_notifications_sudo),
            devices=len(devices),
            unreachable=len(devices_to_unlink),
            retried=len(retry_delay_by_notif_id),
            kept=len(notifs_to_keep),
        )
        (web_push_notifications_sudo - notifs_to_keep).unlink()
        for notif in notifs_to_keep:
            notif.retry_after = now + retry_delay_by_notif_id[notif.id]

        if devices_to_unlink:
            self.env["mail.push.device"].sudo().browse(devices_to_unlink).unlink()

        if self.sudo().search_count(self._get_domain_due(), limit=1) > 0:
            self.env.ref("mail.ir_cron_web_push_notification")._trigger()
