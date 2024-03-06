import { models } from "@web/../tests/web_test_helpers";

export class MailNotification extends models.ServerModel {
    _name = "mail.notification";

    /** @param {number[]} ids */
    _filtered_for_web_client(ids) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const notifications = this._filter([["id", "in", ids]]);
        return notifications.filter((notification) => {
            const partner = ResPartner._filter([["id", "=", notification.res_partner_id]])[0];
            if (
                ["bounce", "exception", "canceled"].includes(notification.notification_status) ||
                (partner && partner.partner_share)
            ) {
                return true;
            }
            const message = MailMessage._filter([["id", "=", notification.mail_message_id]])[0];
            const subtypes = message.subtype_id
                ? MailMessageSubtype._filter([["id", "=", message.subtype_id]])
                : [];
            return subtypes.length === 0 || subtypes[0].track_recipients;
        });
    }

    /** @param {number[]} ids */
    _notification_format(ids) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const notifications = this._filter([["id", "in", ids]]);
        return notifications.map((notification) => {
            const partner = ResPartner._filter([["id", "=", notification.res_partner_id]])[0];
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
