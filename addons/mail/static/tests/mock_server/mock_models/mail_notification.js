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
    _to_store(ids, store) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const notifications = this._filter([["id", "in", ids]]);
        for (const notification of notifications) {
            const partner = ResPartner._filter([["id", "=", notification.res_partner_id]])[0];
            if (partner) {
                store.add("Persona", {
                    displayName: partner.display_name,
                    id: partner.id,
                    type: "partner",
                });
            }
            store.add("Notification", {
                failure_type: notification.failure_type,
                id: notification.id,
                message: { id: notification.mail_message_id },
                notification_status: notification.notification_status,
                notification_type: notification.notification_type,
                persona: partner ? { id: partner.id, type: "partner" } : false,
            });
        }
    }
}
