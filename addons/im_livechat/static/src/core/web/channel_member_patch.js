import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    get canOpenChat() {
        return (
            super.canOpenChat &&
            !this.member.partner_id?.is_public &&
            this.member.livechat_member_type !== "bot"
        );
    },
});
