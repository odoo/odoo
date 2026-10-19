import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    /** @param {import("models").ChannelMember} member */
    canOpenChat(member) {
        return (
            super.canOpenChat(member) &&
            !member.partner_id?.is_public &&
            member.livechat_member_type !== "bot"
        );
    },
});
