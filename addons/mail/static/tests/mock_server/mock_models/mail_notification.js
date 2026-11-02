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

        return this.browse(ids).filter((notification) => {
            const [partner] = ResPartner.browse(notification.res_partner_id);
            if (
                ["bounce", "exception", "canceled"].includes(notification.notification_status) ||
                (partner && partner.partner_share)
            ) {
                return true;
            }
            const [message] = MailMessage.browse(notification.mail_message_id);
            const subtypes = message.subtype_id
                ? MailMessageSubtype.browse(message.subtype_id)
                : [];
            return subtypes.length === 0 || subtypes[0].track_recipients;
        });
    }

    _store_notification_fields(res) {
        res.extend(["failure_type", "mail_message_id"]);
        res.extend(["notification_status", "notification_type"]);
        res.one("res_partner_id", (r) => {
            r.extend(["name", "email_normalized"]);
            r.attr("email", undefined, { predicate: (p) => !p.email_normalized });
            r.attr("display_name", undefined, { predicate: (p) => !p.name });
        });
        if (res.is_for_internal_users()) {
            res.attr("mail_email_address");
        }
    }
}
