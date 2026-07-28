import { models } from "@web/../tests/web_test_helpers";

export class MailMessageReaction extends models.ServerModel {
    _name = "mail.message.reaction";
<<<<<<< a5db52fe916061e16bde55f411fa072b4e9105d9
||||||| 3b5eb0e1c36ef72c579f13f367f51c58a19205a1

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
=======

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
                sequence: Math.min(...reactionGroup.map((reaction) => reaction.id)),
            };
            store.add("MessageReactions", data);
        }
    }
>>>>>>> 98feb25ccf9378d6d9c383421e5f9cfe25dcd3cb
}
