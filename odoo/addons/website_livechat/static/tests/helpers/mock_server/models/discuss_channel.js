/** @odoo-module **/

import "@im_livechat/../tests/helpers/mock_server/models/discuss_channel"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Overrides to add visitor information to livechat channels.
     *
     * @override
     */
    _mockDiscussChannelChannelInfo(ids) {
        const channelInfos = super._mockDiscussChannelChannelInfo(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this.getRecords("discuss.channel", [["id", "=", channelInfo.id]])[0];
            if (channel.channel_type === "livechat" && channel.livechat_visitor_id) {
                const visitor = this.getRecords("website.visitor", [
                    ["id", "=", channel.livechat_visitor_id],
                ])[0];
                const partner = this.getRecords("res.partner", [
                    ["id", "=", visitor.partner_id],
                ])[0];
                const country = this.getRecords("res.country", [
                    ["id", "=", visitor.country_id],
                ])[0];
                channelInfo.visitor = {
                    country_code: country && country.code,
                    country_id: country && country.id,
                    display_name: partner?.name ?? partner?.display_name ?? visitor.display_name,
                    history: visitor.history, // TODO should be computed
                    id: visitor.id,
                    is_connected: visitor.is_connected,
                    lang_name: visitor.lang_name,
                    partner_id: visitor.partner_id,
                    type: "visitor",
                    website_name: visitor.website_name,
                };
            }
        }
        return channelInfos;
    },
});
