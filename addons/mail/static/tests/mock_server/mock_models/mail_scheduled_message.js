import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { fields, getKwArgs, makeKwArgs, models, serverState } from "@web/../tests/web_test_helpers";

export class MailScheduledMessage extends models.ServerModel {
    _inherit = "mail.scheduled.message";

    author_id = fields.Generic({ default: () => serverState.partnerId });

    post_message(ids, send_bus_notification = true) {
        const kwargs = getKwArgs(arguments, "ids", "send_bus_notification");
        ids = kwargs.ids;
        send_bus_notification =
            kwargs.send_bus_notification === undefined ? true : kwargs.send_bus_notification;
        const id = ids;
        const [scheduledMessage] = this.browse(id);
        this.env["mail.thread"].message_post.call(
            this.env[scheduledMessage.model],
            [scheduledMessage.res_id],
            {
                ...makeKwArgs({
                    attachment_ids: scheduledMessage.attachment_ids,
                    author_id: scheduledMessage.author_id,
                    subject: scheduledMessage.subject,
                    body: scheduledMessage.body,
                    partner_ids: scheduledMessage.partner_ids,
                    subtype_xmlid: scheduledMessage.is_note ? "mail.mt_note" : "mail.mt_comment",
                    ...JSON.parse(scheduledMessage.notification_parameters || "{}"),
                }),
                model: scheduledMessage.model,
            }
        );
        if (send_bus_notification) {
            this.env["bus.bus"]._sendone(this.author_id, "mail.scheduled_message/posted", {
                res_model: scheduledMessage.model,
                res_id: scheduledMessage.res_id,
            });
        }
        this.unlink(ids);
    }

    reset_attachments_in_composer(ids) {}

    _to_store(store) {
        /** @type {import("mock_models").IrAttachment} */
        const IrAttachment = this.env["ir.attachment"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        for (const message of this) {
            store.add("mail.scheduled.message", {
                attachment_ids: mailDataHelpers.Store.many(
                    IrAttachment.browse(message.attachment_ids)
                ),
                author_id: mailDataHelpers.Store.one(ResPartner.browse(message.author_id)),
                body: ["markup", message.body],
                id: message.id,
                scheduled_date: message.scheduled_date,
                subject: message.subject,
                is_note: message.is_note,
            });
        }
    }
}
