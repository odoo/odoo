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
                new mailDataHelpers.Store(channel)
                    .add(channel, { open_chat_window: true })
                    .get_result()
            );
        }
    }

    _to_store(store) {
        super._to_store(store);
        /** @type {import("mock_models").WebsiteTrack} */
        const WebsiteTrack = this.env["website.track"];
        const WebsitePage = this.env["website.page"];
        for (const visitor of this) {
            const visitor_model = this.browse(visitor.id);
            const [data] = this._read_format(visitor.id, []);
            const track_records = WebsiteTrack.search_read(
                [
                    ["res_model", "=", "website.page"],
                    ["res_id", "!=", false],
                    ["visitor_id", "=", visitor.id],
                ],
                { limit: 3 }
            );
            // Add track records to the store with only the fields the frontend needs.
            store.add(WebsiteTrack.browse(track_records.map((t) => t.id)), [
                "res_model",
                "res_id",
                "visit_datetime",
            ]);
            // Add referenced website.page records so the frontend resRecord getter
            // can resolve them by res_id.
            store.add(WebsitePage.browse(track_records.map((t) => t.res_id).filter(Boolean)), [
                "name",
            ]);
            // Sort newest first (visit_datetime DESC, id DESC) to match Python ordering.
            data.last_track_ids = track_records
                .sort((a, b) => {
                    if (a.visit_datetime === b.visit_datetime) {
                        return b.id - a.id;
                    }
                    return a.visit_datetime < b.visit_datetime ? 1 : -1;
                })
                .map((t) => t.id);
            store._add_record_fields(visitor_model, data);
        }
    }
}
