/* @odoo-module */

import { ChannelMember } from "@mail/core/common/channel_member_model";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    getLangName() {
        if (this.persona.is_public && this.thread.visitor?.langName) {
            return this.thread.visitor.langName;
        }
        return super.getLangName();
    },
});
