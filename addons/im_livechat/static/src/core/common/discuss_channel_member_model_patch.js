import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const discussChannelMemberPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {"agent"|"bot"|"visitor"} */
        this.livechat_member_type = undefined;
    },
    get canRemoveAdmin() {
        return !this.isLivechatMember && super.canRemoveAdmin;
    },
    get canRemoveMember() {
        if (this.isLivechatMember) {
            // Agents are owners of live chats but removing members is limited to channels
            // and groups.
            return this.store.self_user?.is_admin;
        }
        return super.canRemoveMember;
    },
    get canRemoveOwner() {
        return !this.isLivechatMember && super.canRemoveOwner;
    },
    get canSetAdmin() {
        return !this.isLivechatMember && super.canSetAdmin;
    },
    get canSetOwner() {
        return !this.isLivechatMember && super.canSetOwner;
    },
    /** Roles of live chat members depend on their type and cannot be modified. */
    get isLivechatMember() {
        return this.channel_id?.channel_type === "livechat";
    },
};
patch(ChannelMember.prototype, discussChannelMemberPatch);
