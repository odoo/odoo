import { mailModels } from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    /**
     * @override
     */
    _init_store_data(store) {
        super._init_store_data(...arguments);
        store.add({
            has_access_livechat: this.env.user?.group_ids.includes(serverState.groupLivechatId),
        });
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const pinnedMembers = DiscussChannelMember._filter([
            ["partner_id", "=", this.env.user.partner_id],
        ]).filter((member) => member.is_pinned);
        store.add({
            show_livechat_category: pinnedMembers.length > 0,
        });
        store.add(this.browse(this.env.uid), {
            is_livechat_manager: this.env.user?.group_ids.includes(
                serverState.groupLivechatManagerId
            ),
        });
    }
}
