import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

function historyDataToString(history) {
    const formatDateTime = (dateTime) => {
        const match = dateTime.match(/.* ([0-9]{2}:[0-9]{2}:)/);
        return match ? match[1].slice(0, -1) : "";
    };
    return history.map((h) => `${h[0]} (${formatDateTime(h[1])})`).join(" → ");
}

export class DiscussChannel extends livechatModels.DiscussChannel {
    livechat_visitor_id = fields.Many2one({ relation: "website.visitor", string: "Visitor" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(ids, store) {
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

        super._to_store(...arguments);
        const channels = this.browse(ids);
        for (const channel of channels) {
            if (channel.channel_type === "livechat" && channel.livechat_visitor_id) {
                const channelInfo = {};
                const [visitor] = WebsiteVisitor.browse(channel.livechat_visitor_id);
                const [partner] = ResPartner.browse(visitor.partner_id);
                const [country] = ResCountry.browse(visitor.country_id);
                const visitorHistoryData = JSON.parse(visitor.history_data || "[]");

                channelInfo.visitor = {
                    country: country ? { id: country.id, code: country.code } : false,
                    name: partner?.name || partner?.display_name || visitor.display_name || `Visitor #${visitor.id}`,
                    history: historyDataToString(visitorHistoryData),
                    history_data: visitorHistoryData,
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
                store.add(this.browse(channel.id), channelInfo);
            }
        }
    }
}
