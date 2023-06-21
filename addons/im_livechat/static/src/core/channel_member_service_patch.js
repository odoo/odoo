/* @odoo-module */

import { ChannelMemberService } from "@mail/core/common/channel_member_service";
import { patch } from "@web/core/utils/patch";

patch(ChannelMemberService, "im_livechat", {
    getName(member) {
        if (member.thread.type !== "livechat") {
            return this._super();
        }
        if (member.persona.user_livechat_username) {
            return member.persona.user_livechat_username;
        }
        if (member.persona.is_public) {
            return member.thread.anonymous_name;
        }
        return this._super();
    },
});
