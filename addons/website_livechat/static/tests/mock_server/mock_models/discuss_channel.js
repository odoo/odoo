import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends livechatModels.DiscussChannel {
    livechat_visitor_id = fields.Many2one({ relation: "website.visitor", string: "Visitor" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_channel_info"]}
     */
    _channel_info(ids) {
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").Website} */
        const Website = this.env["website"];
        /** @type {import("mock_models").WebsiteVisitor} */
        const WebsiteVisitor = this.env["website.visitor"];

        const channelInfos = super._channel_info(...arguments);
        for (const channelInfo of channelInfos) {
            const [channel] = this._filter([["id", "=", channelInfo.id]]);
            if (channel.channel_type === "livechat" && channel.livechat_visitor_id) {
                const [visitor] = WebsiteVisitor._filter([
                    ["id", "=", channel.livechat_visitor_id],
                ]);
                const [partner] = ResPartner._filter([["id", "=", visitor.partner_id]]);
                const [country] = ResCountry._filter([["id", "=", visitor.country_id]]);
                channelInfo.visitor = {
                    country: country ? { id: country.id, code: country.code } : false,
                    name: partner?.name ?? partner?.display_name ?? visitor.display_name,
                    history: visitor.history, // TODO should be computed
                    id: visitor.id,
                    is_connected: visitor.is_connected,
                    lang_name: visitor.lang_id ? ResLang.read(visitor.lang_id)[0].name : false,
                    visitorPartner: visitor.partner_id
                        ? { id: visitor.partner_id, type: "partner" }
                        : false,
                    type: "visitor",
                    website_name: visitor.website_id
                        ? Website.read(visitor.website_id)[0].name
                        : false,
                };
            }
        }
        return channelInfos;
    }
}
