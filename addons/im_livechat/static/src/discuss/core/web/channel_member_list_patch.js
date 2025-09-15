import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { patch } from "@web/core/utils/patch";

patch(ChannelMemberList.prototype, {
    canOpenChatWith(member) {
        return (
            super.canOpenChatWith(member) &&
            !member.partner_id?.is_public &&
            member.livechat_member_type !== "bot"
        );
    },
});
