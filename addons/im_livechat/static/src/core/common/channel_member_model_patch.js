import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const channelMemberPatch = {
    get name() {
        if (this.thread.channel_type === "livechat" && this.persona.user_livechat_username) {
            return this.persona.user_livechat_username;
        }
        if (this.persona.is_public) {
            return this.thread.anonymous_name;
        }
        return super.name;
    },
};
patch(ChannelMember.prototype, channelMemberPatch);
