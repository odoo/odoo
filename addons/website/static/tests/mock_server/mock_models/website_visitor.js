import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { Command, fields, makeKwArgs, models, serverState } from "@web/../tests/web_test_helpers";

export class WebsiteVisitor extends models.ServerModel {
    _name = "website.visitor";

    country_id = fields.Many2one({ relation: "res.country", string: "Country" }); // FIXME: somehow not fetched properly
    display_name = fields.Char({ compute: "_compute_display_name" });
    history = fields.Char();
    lang_id = fields.Many2one({ relation: "res.lang", string: "Language" }); // FIXME: somehow not fetched properly
    partner_id = fields.Many2one({ relation: "res.partner", string: "Contact" }); // FIXME: somehow not fetched properly
    website_id = fields.Many2one({ relation: "website", string: "Website" });

    _compute_display_name() {
        for (const record of this) {
            record.display_name =
                this.env["res.partner"].browse(record.partner_id)[0]?.name ||
                `Website Visitor #${record.id}`;
        }
    }

    /** @param {number[]} ids */
    _to_store(ids, store) {
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").Website} */
        const Website = this.env["website"];

        for (const visitor of this.browse(ids)) {
            const [data] = this._read_format(visitor.id, ["display_name"]);
            data.country_id = mailDataHelpers.Store.one(ResCountry.browse(visitor.country_id));
            data.history = visitor.history;
            data.lang_id = mailDataHelpers.Store.one(ResLang.browse(visitor.lang_id));
            data.partner_id = mailDataHelpers.Store.one(
                ResPartner.browse(visitor.partner_id),
                makeKwArgs({ fields: ["country_id"] })
            );
            data.website_id = mailDataHelpers.Store.one(Website.browse(visitor.website_id));
            store.add(this.browse(visitor.id), data);
        }
    }

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
                livechat_active: true,
                livechat_operator_id: serverState.partnerId,
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
