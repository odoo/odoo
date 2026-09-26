import { ResPartner } from "@mail/../tests/mock_server/mock_models/res_partner";

import { serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    _search_for_channel_invite_to_store(ids, store, channel_id) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const [channel] = DiscussChannel.browse(channel_id);
        store.add(this.browse(ids), "_store_channel_invite_fields", {
            fields_params: { channel },
        });
    },

    _store_channel_invite_fields(res, { channel } = {}) {
        super._store_channel_invite_fields(res, { channel });
        if (channel?.channel_type !== "livechat" || !this.length) {
            return;
        }

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const activeLivechatPartners = LivechatChannel._filter([])
            .map(({ available_operator_ids }) => available_operator_ids)
            .flat()
            .map((userId) => ResUsers.browse(userId)[0].partner_id);
        const inviteBySelfCount = (partner) =>
            DiscussChannelMember.search_count([
                ["partner_id", "=", partner.id],
                ["create_uid", "=", serverState.userId],
            ]);
        const languagesByPartner = (partner) => {
            const langs = [];
            if (partner.lang) {
                langs.push(ResLang.search_read([["code", "=", partner.lang]])[0].name);
            }
            for (const userId of partner.user_ids) {
                const [user] = ResUsers.browse(userId);
                for (const langId of user?.livechat_lang_ids ?? []) {
                    const [lang] = ResLang.browse(langId);
                    if (lang && !langs.includes(lang.name)) {
                        langs.push(lang.name);
                    }
                }
            }
            return langs;
        };
        res.attr("invite_by_self_count", (p) => inviteBySelfCount(p));
        res.attr("is_available", (p) => activeLivechatPartners.includes(p.id));
        res.attr("lang_name", (p) => languagesByPartner(p)[0]);
        res.attr("livechat_languages", (p) => languagesByPartner(p).slice(1));
        // sudo: res.users.settings - operator can access other operators livechat usernames
        res.attr("user_livechat_username", undefined, { sudo: true });
        // sudo - res.partner: checking if operator is in call for live chat invitation is acceptable.
        res.attr("is_in_call", undefined, { sudo: true });
        res.one("main_user_id", (mainUserRes) => {
            mainUserRes.attr("partner_id");
            mainUserRes.many("livechat_expertise_ids", ["name"]);
        });
        res.many("user_ids", ["active", "company_ids", "share"], { internal: true, sudo: true });
    },

    _store_livechat_member_fields(res) {
        this._store_avatar_fields(res);
        this._store_livechat_username_fields(res);
    },

    _store_livechat_username_fields(res) {
        res.attr("name", undefined, { predicate: (p) => !p.user_livechat_username });
        res.attr("user_livechat_username");
    },
});
