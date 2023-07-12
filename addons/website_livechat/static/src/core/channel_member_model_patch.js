/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, "website_livechat", {
    getLangName() {
        if (this.persona.is_public && this.thread.visitor?.langName) {
            return this.thread.visitor.langName;
        }
        return this._super(this);
    },
});
