import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { fields, models, serverState } from "@web/../tests/web_test_helpers";

export class MailScheduledMessage extends models.ServerModel {
    _inherit = "mail.scheduled.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });

    _to_store(ids, store) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages = this.browse(ids);
        for (const message of messages) {
            store.add("mail.scheduled.message", {
                attachment_ids: mailDataHelpers.Store.many(
                    IrAttachment.browse(message.attachment_ids)
                ),
                author: mailDataHelpers.Store.one(ResPartner.browse(message.author_id)),
                body: message.body,
                id: message.id,
                scheduled_date: message.scheduled_date,
                subject: message.subject,
                is_note: message.is_note,
            });
        }
    }
}
