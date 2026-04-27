import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const channelMemberListPatch = {
    canOpenChatWith(member) {
        return (
            super.canOpenChatWith(member) && member.persona.notEq(member.thread.whatsapp_partner_id)
        );
    },
};

patch(ChannelMemberList.prototype, channelMemberListPatch);
