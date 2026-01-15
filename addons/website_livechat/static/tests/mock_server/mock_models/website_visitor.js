import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { Command, serverState } from "@web/../tests/web_test_helpers";
import { websiteModels } from "@website/../tests/helpers";

export class WebsiteVisitor extends websiteModels.WebsiteVisitor {
    _inherit = "website.visitor";

    /** @param {integer[]} ids */
    action_send_chat_request(ids) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const visitors = this.browse(ids);
        for (const visitor of visitors) {
            const operator = this.env.user;
            const country = visitor.country_id ? ResCountry.browse(visitor.country_id) : undefined;
            const visitor_name = `Visitor #${visitor.id}${country ? ` (${country.name})` : ""}`;
            const membersToAdd = [Command.create({ partner_id: serverState.partnerId })];
            if (visitor.partner_id) {
                membersToAdd.push(Command.create({ partner_id: visitor.partner_id }));
            }
            const livechatId = DiscussChannel.create({
                channel_member_ids: membersToAdd,
                channel_type: "livechat",
                livechat_operator_id: serverState.partnerId,
                name: `${visitor_name}, ${
                    operator.livechat_username ? operator.livechat_username : operator.name
                }`,
            });
            if (!visitor.partner_id) {
                const guestId = MailGuest.create({ name: `Visitor #${visitor.id}` });
                DiscussChannel.write([livechatId], {
                    channel_member_ids: [Command.create({ guest_id: guestId })],
                });
            }
            const [partner] = ResPartner.read(serverState.partnerId);
            const channel = DiscussChannel.browse(livechatId);
            // notify operator
            BusBus._sendone(
                partner,
                "mail.record/insert",
                new mailDataHelpers.Store(channel)
                    .add(channel, { open_chat_window: true })
                    .get_result()
            );
        }
    }
}
