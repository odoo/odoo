/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_notification default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_filtered_for_web_client` on `mail.notification`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailNotification_FilteredForWebClient(ids) {
        const notifications = this.getRecords("mail.notification", [["id", "in", ids]]);
        return notifications.filter((notification) => {
            const partner = this.getRecords("res.partner", [
                ["id", "=", notification.res_partner_id],
            ])[0];
            if (
                ["bounce", "exception", "canceled"].includes(notification.notification_status) ||
                (partner && partner.partner_share)
            ) {
                return true;
            }
            const message = this.getRecords("mail.message", [
                ["id", "=", notification.mail_message_id],
            ])[0];
            const subtypes = message.subtype_id
                ? this.getRecords("mail.message.subtype", [["id", "=", message.subtype_id]])
                : [];
            return subtypes.length == 0 || subtypes[0].track_recipients;
        });
    },
    /**
     * Simulates `_notification_format` on `mail.notification`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Object[]}
     */
    _mockMailNotification_NotificationFormat(ids) {
        const notifications = this.getRecords("mail.notification", [["id", "in", ids]]);
        return notifications.map((notification) => {
            const partner = this.getRecords("res.partner", [
                ["id", "=", notification.res_partner_id],
            ])[0];
            return {
                id: notification.id,
                notification_type: notification.notification_type,
                notification_status: notification.notification_status,
                failure_type: notification.failure_type,
                persona: partner
                    ? { id: partner.id, name: partner.name, type: "partner" }
                    : undefined,
            };
        });
    },
});
