import { mailModels } from "@mail/../tests/mail_test_helpers";

import { getKwArgs, makeKwArgs, serverState } from "@web/../tests/web_test_helpers";

export class ResPartner extends mailModels.ResPartner {
    /**
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["_search_for_channel_invite_to_store"]}
     */
    _search_for_channel_invite_to_store(ids, store, channel_id) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").Im_LivechatExpertise} */
        const Im_LivechatExpertise = this.env["im_livechat.expertise"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        super._search_for_channel_invite_to_store(ids, store, channel_id);
        const [channel] = DiscussChannel.browse(channel_id);
        if (channel?.channel_type !== "livechat") {
            return;
        }
        const activeLivechatPartners = LivechatChannel._filter([])
            .map(({ available_operator_ids }) => available_operator_ids)
            .flat()
            .map((userId) => ResUsers.browse(userId)[0].partner_id);
        for (const partner of ResPartner.browse(ids)) {
            const data = {
                invite_by_self_count: DiscussChannelMember.search_count([
                    ["partner_id", "=", partner.id],
                    ["create_uid", "=", serverState.userId],
                ]),
                is_available: activeLivechatPartners.includes(partner.id),
            };
            if (partner.lang) {
                data.lang_name = ResLang.search_read([["code", "=", partner.lang]])[0].name;
            }
            if (partner.user_ids.length) {
                const [user] = ResUsers.browse(partner.user_ids[0]);
                if (user) {
                    const userLangs = user.livechat_lang_ids
                        .map((langId) => ResLang.browse(langId)[0])
                        .filter((lang) => lang.name !== data.lang_name);
                    data.livechat_languages = userLangs.map((lang) => lang.name);
                    data.livechat_expertise = user.livechat_expertise_ids.map(
                        (expId) => Im_LivechatExpertise.browse(expId)[0].name
                    );
                }
            }
            store.add(this.browse(partner.id), makeKwArgs({ fields: ["user_livechat_username"] }));
            store.add(this.browse(partner.id), data);
            store.add(this.browse(partner.id), makeKwArgs({ extra_fields: ["is_in_call"] }));
        }
    }
    /**
     * @override
     * @type {typeof mailModels.ResPartner["prototype"]["_to_store"]}
     */
    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        fields = kwargs.fields;

        super._to_store(...arguments);
        if (fields && fields.includes("user_livechat_username")) {
            store._add_record_fields(
                this.filter((partner) => !partner.user_livechat_username),
                ["name"]
            );
        }
    }
}
