/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/res_partner"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockResPartnerSearchForChannelInvite(search_term, channel_id, limit = 30) {
        const result = super._mockResPartnerSearchForChannelInvite(search_term, channel_id, limit);
        const [channel] = this.pyEnv["discuss.channel"].searchRead([["id", "=", channel_id]]);
        if (channel.channel_type !== "livechat") {
            return result;
        }
        const activeLivechatPartners = this.pyEnv["im_livechat.channel"]
            .searchRead([])
            .map(({ available_operator_ids }) => available_operator_ids)
            .flat()
            .map(
                (userId) =>
                    this.pyEnv["res.users"].searchRead([["id", "=", userId]])[0].partner_id[0]
            );
        for (const partner of result["partners"]) {
            partner.is_available = activeLivechatPartners.includes(partner.id);
            if (partner.lang) {
                partner.lang_name = this.pyEnv["res.lang"].searchRead([
                    ["code", "=", partner.lang],
                ])[0].name;
            }
            partner.invite_by_self_count = this.pyEnv["discuss.channel.member"].searchCount([
                ["partner_id", "=", partner.id],
                ["create_uid", "=", this.pyEnv.currentUserId],
            ]);
        }
        return result;
    },
    /**
     * Overrides to add out of office to employees.
     *
     * @override
     */
    _mockResPartnerMailPartnerFormat(ids) {
        const partnerFormats = super._mockResPartnerMailPartnerFormat(...arguments);
        const partners = this.getRecords("res.partner", [["id", "in", ids]], {
            active_test: false,
        });
        for (const partner of partners) {
            // Not a real field but ease the testing
            partnerFormats.get(partner.id).user_livechat_username = partner.user_livechat_username;
        }
        return partnerFormats;
    },
});
