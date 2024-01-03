/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";

export class MailNotification extends models.ServerModel {
    _name = "mail.notification";

    /**
     * Simulates `_filtered_for_web_client` on `mail.notification`.
     *
     * @param {number[]} ids
     */
    _filteredForWebClient(ids) {
        const notifications = this._filter([["id", "in", ids]]);
        return notifications.filter((notification) => {
            const partner = this.env["res.partner"]._filter([
                ["id", "=", notification.res_partner_id],
            ])[0];
            if (
                ["bounce", "exception", "canceled"].includes(notification.notification_status) ||
                (partner && partner.partner_share)
            ) {
                return true;
            }
            const message = this.env["mail.message"]._filter([
                ["id", "=", notification.mail_message_id],
            ])[0];
            const subtypes = message.subtype_id
                ? this.env["mail.message.subtype"]._filter([["id", "=", message.subtype_id]])
                : [];
            return subtypes.length == 0 || subtypes[0].track_recipients;
        });
    }

    /**
     * Simulates `_notification_format` on `mail.notification`.
     *
     * @param {number[]} ids
     */
    _notificationFormat(ids) {
        const notifications = this._filter([["id", "in", ids]]);
        return notifications.map((notification) => {
            const partner = this.env["res.partner"]._filter([
                ["id", "=", notification.res_partner_id],
            ])[0];
            return {
                id: notification.id,
                notification_type: notification.notification_type,
                notification_status: notification.notification_status,
                failure_type: notification.failure_type,
                persona: partner
                    ? { id: partner.id, displayName: partner.display_name, type: "partner" }
                    : undefined,
            };
        });
    }
}
