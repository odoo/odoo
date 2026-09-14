// @ts-check
/** @odoo-module native */
import { odooExceptionTitleMap } from "@web/components/errors/error_dialogs";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { session } from "@web/session";

export const MAIL_DELIVERY_ERROR =
    "odoo.addons.mail.models.ir_mail_server.MailDeliveryError";

odooExceptionTitleMap.set(MAIL_DELIVERY_ERROR, _t("MailDeliveryError"));

if (session.is_frontend) {
    registry.category("error_notifications").add(MAIL_DELIVERY_ERROR, {
        title: _t("MailDeliveryError"),
        type: "warning",
        sticky: true,
    });
}
