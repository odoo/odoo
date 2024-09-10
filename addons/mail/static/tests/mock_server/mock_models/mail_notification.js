import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { makeKwArgs, models } from "@web/../tests/web_test_helpers";

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

    /** @param {number[]} ids */
    _to_store(ids, store) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        for (const notification of this.browse(ids)) {
            const [data] = this.read(
                notification.id,
                ["failure_type", "notification_status", "notification_type"],
                makeKwArgs({ load: false })
            );
            data.message = mailDataHelpers.Store.one(
                this.env["mail.message"].browse(notification.mail_message_id),
                makeKwArgs({ only_id: true })
            );
            data.persona = mailDataHelpers.Store.one(
                ResPartner.browse(notification.res_partner_id),
                makeKwArgs({ fields: ["name"] })
            );
            store.add(this.browse(notification.id), data);
        }
    }
}
