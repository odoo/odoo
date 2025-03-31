import { makeKwArgs, models } from "@web/../tests/web_test_helpers";
import { groupBy } from "@web/core/utils/arrays";
import { mailDataHelpers } from "../mail_mock_server";

export class MailMessageReaction extends models.ServerModel {
    _name = "mail.message.reaction";

    _to_store(ids, store) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const reactionGroups = groupBy(this.browse(ids), (r) => [r.message_id, r.content]);
        for (const groupId in reactionGroups) {
            const reactionGroup = reactionGroups[groupId];
            const { message_id, content } = reactionGroups[groupId][0];
            const guests = MailGuest.browse(reactionGroup.map((reaction) => reaction.guest_id));
            const partners = ResPartner.browse(
                reactionGroup.map((reaction) => reaction.partner_id)
            );
            store.add(guests, makeKwArgs({ fields: ["avatar_128", "name"] }));
            store.add(partners, makeKwArgs({ fields: ["avatar_128", "name"] }));
            const data = {
                content: content,
                count: reactionGroup.length,
                sequence: Math.min(reactionGroup.map((reaction) => reaction.id)),
                personas: mailDataHelpers.Store.many_ids(guests).concat(
                    mailDataHelpers.Store.many_ids(partners)
                ),
                message: mailDataHelpers.Store.one_id(MailMessage.browse(message_id)),
            };
            store.add("MessageReactions", data);
        }
    }
}
