import { Store } from "@mail/../tests/mock_server/store";

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
            const membersToAdd = [
                Command.create({
                    partner_id: serverState.partnerId,
                    livechat_member_type: "agent",
                }),
            ];
            if (visitor.partner_id) {
                membersToAdd.push(
                    Command.create({
                        partner_id: visitor.partner_id,
                        livechat_member_type: "visitor",
                    })
                );
            } else {
                const guestId = MailGuest.create({ name: `Visitor #${visitor.id}` });
                membersToAdd.push(
                    Command.create({
                        guest_id: guestId,
                        livechat_member_type: "visitor",
                    })
                );
            }
            const livechatId = DiscussChannel.create({
                channel_member_ids: membersToAdd,
                channel_type: "livechat",
                name: `${visitor_name}, ${
                    operator.livechat_username ? operator.livechat_username : operator.name
                }`,
            });
            const [partner] = ResPartner.read(serverState.partnerId);
            const channel = DiscussChannel.browse(livechatId);
            // notify operator
            BusBus._sendone(
                partner,
                "mail.record/insert",
                new Store().add(channel, "_store_open_chat_window_fields").as_dict()
            );
        }
    }

    _store_visitor_history_fields(res) {
        /** @type {import("mock_models").WebsiteTrack} */
        const WebsiteTrack = this.env["website.track"];

        res.many(
            "last_track_ids",
            (trackRes) => {
                trackRes.one("page_id", ["name", "url"]);
                trackRes.attr("visit_datetime");
            },
            {
                sort: (a, b) => {
                    if (a.visit_datetime === b.visit_datetime) {
                        return a.id - b.id;
                    }
                    return a.visit_datetime < b.visit_datetime ? 1 : -1;
                },
                value: (visitor) =>
                    WebsiteTrack.browse(
                        WebsiteTrack.search_read(
                            [
                                ["page_id", "!=", false],
                                ["visitor_id", "=", visitor.id],
                            ],
                            { limit: 3 }
                        ).map((t) => t.id)
                    ),
            }
        );
    }
}
