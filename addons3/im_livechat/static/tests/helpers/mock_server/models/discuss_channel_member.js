/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/discuss_channel_member"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockDiscussChannelMember_GetPartnerData(ids) {
        const [member] = this.getRecords("discuss.channel.member", [["id", "in", ids]]);
        const [channel] = this.getRecords("discuss.channel", [["id", "=", member.channel_id]]);
        const [partner] = this.getRecords("res.partner", [["id", "=", member.partner_id]], {
            active_test: false,
        });
        if (channel.channel_type === "livechat") {
            const data = {
                id: partner.id,
                is_public: partner.is_public,
            };
            if (partner.user_livechat_username) {
                data["user_livechat_username"] = partner.user_livechat_username;
            } else {
                data["name"] = partner.name;
            }
            if (!partner.is_public) {
                const [country] = this.getRecords("res.country", [["id", "=", partner.country_id]]);
                data["country"] = country
                    ? {
                          code: country.code,
                          id: country.id,
                          name: country.name,
                      }
                    : false;
            }
            return data;
        }
        return super._mockDiscussChannelMember_GetPartnerData(ids);
    },
});
