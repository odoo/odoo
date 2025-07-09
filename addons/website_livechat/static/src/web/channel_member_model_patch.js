import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const channelMemberPatch = {
    getLangName() {
        if (this.partner_id?.is_public && this.channel_id?.livechat_visitor_id?.lang_id?.name) {
            return this.channel_id.livechat_visitor_id.lang_id.name;
        }
        return super.getLangName();
    },
};
patch(ChannelMember.prototype, channelMemberPatch);
