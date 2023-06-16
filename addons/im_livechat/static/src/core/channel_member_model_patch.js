/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, "im_livechat", {
    get displayName() {
        if (this.thread?.type !== "livechat") {
            return this._super();
        }
        if (this.persona?.user_livechat_username) {
            return this.persona.user_livechat_username;
        }
        if (this.persona?.is_public) {
            return this.thread.displayName;
        }
        return this._super();
    },
});
