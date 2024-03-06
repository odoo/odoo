import { serverState } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    /**
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["search_for_channel_invite"]}
     */
    search_for_channel_invite(search_term, channel_id, limit = 30) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const result = super.search_for_channel_invite(search_term, channel_id, limit);
        const [channel] = DiscussChannel.search_read([["id", "=", channel_id]]);
        if (channel.channel_type !== "livechat") {
            return result;
        }
        const activeLivechatPartners = LivechatChannel.search_read([])
            .map(({ available_operator_ids }) => available_operator_ids)
            .flat()
            .map((userId) => ResUsers.search_read([["id", "=", userId]])[0].partner_id[0]);
        for (const partner of result["partners"]) {
            partner.is_available = activeLivechatPartners.includes(partner.id);
            if (partner.lang) {
                partner.lang_name = ResLang.search_read([["code", "=", partner.lang]])[0].name;
            }
            partner.invite_by_self_count = DiscussChannelMember.search_count([
                ["partner_id", "=", partner.id],
                ["create_uid", "=", serverState.userId],
            ]);
        }
        return result;
    }
    /**
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["mail_partner_format"]}
     */
    mail_partner_format(ids) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const partnerFormats = super.mail_partner_format(...arguments);
        const partners = ResPartner._filter([["id", "in", ids]], {
            active_test: false,
        });
        for (const partner of partners) {
            // Not a real field but ease the testing
            partnerFormats[partner.id].user_livechat_username = partner.user_livechat_username;
        }
        return partnerFormats;
    }
}
