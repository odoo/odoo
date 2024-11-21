import { ChannelMember } from "@mail/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    get name() {
        if (this.thread.channel_type === "livechat" && this.persona.user_livechat_username) {
            return this.persona.user_livechat_username;
        }
        if (this.persona.is_public) {
            return this.thread.anonymous_name;
        }
        return super.name;
    },
});
