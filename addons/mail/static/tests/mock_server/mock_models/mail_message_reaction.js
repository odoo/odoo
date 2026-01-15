import { makeKwArgs, models } from "@web/../tests/web_test_helpers";
import { groupBy } from "@web/core/utils/arrays";
import { mailDataHelpers } from "../mail_mock_server";

export class MailMessageReaction extends models.ServerModel {
    _name = "mail.message.reaction";

    _to_store(store) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const reactionGroups = groupBy(this, (r) => [r.message_id, r.content]);
        for (const groupId in reactionGroups) {
            const reactionGroup = reactionGroups[groupId];
            const { message_id, content } = reactionGroups[groupId][0];
            const guests = MailGuest.browse(reactionGroup.map((reaction) => reaction.guest_id));
            const partners = ResPartner.browse(
                reactionGroup.map((reaction) => reaction.partner_id)
            );
            const data = {
                content: content,
                count: reactionGroup.length,
                guests: mailDataHelpers.Store.many(
                    guests,
                    makeKwArgs({ fields: ["avatar_128", "name"] })
                ),
                message: message_id,
                partners: mailDataHelpers.Store.many(
                    partners,
                    makeKwArgs({ fields: ["avatar_128", "name"] })
                ),
                sequence: Math.min(reactionGroup.map((reaction) => reaction.id)),
            };
            store.add("MessageReactions", data);
        }
    }
}
