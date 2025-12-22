import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { Command, fields, models, serverState } from "@web/../tests/web_test_helpers";

export class WebsiteVisitor extends models.ServerModel {
    _name = "website.visitor";

    country_id = fields.Many2one({ relation: "res.country", string: "Country" }); // FIXME: somehow not fetched properly
    history_data = fields.Char();
    lang_id = fields.Many2one({ relation: "res.lang", string: "Language" }); // FIXME: somehow not fetched properly
    name = fields.Char({ string: "Name" }); // FIXME: somehow not fetched
    partner_id = fields.Many2one({ relation: "res.partner", string: "Contact" }); // FIXME: somehow not fetched properly

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
            const country = visitor.country_id ? ResCountry.browse(visitor.country_id) : undefined;
            const visitor_name = `${visitor.display_name}${country ? `(${country.name})` : ""}`;
            const membersToAdd = [Command.create({ partner_id: serverState.partnerId })];
            if (visitor.partner_id) {
                membersToAdd.push(Command.create({ partner_id: visitor.partner_id }));
            }
            const livechatId = DiscussChannel.create({
                anonymous_name: visitor_name,
                channel_member_ids: membersToAdd,
                channel_type: "livechat",
                livechat_operator_id: serverState.partnerId,
            });
            if (!visitor.partner_id) {
                const guestId = MailGuest.create({ name: `Visitor #${visitor.id}` });
                DiscussChannel.write([livechatId], {
                    channel_member_ids: [Command.create({ guest_id: guestId })],
                });
            }
            const [partner] = ResPartner.read(serverState.partnerId);
            // notify operator
            BusBus._sendone(
                partner,
                "website_livechat.send_chat_request",
                new mailDataHelpers.Store(DiscussChannel.browse(livechatId)).get_result()
            );
        }
    }
}
