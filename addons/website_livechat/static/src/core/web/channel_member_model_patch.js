import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
import { patchModel } from "@mail/model/export";

export const channelMemberPatch = patchModel(ChannelMember, {
    getLangName() {
        if (this.partner_id?.is_public && this.channel_id?.livechat_visitor_id?.lang_id?.name) {
            return this.channel_id.livechat_visitor_id.lang_id.name;
        }
        return super.getLangName();
    },
});
