import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get outOfOfficeDateEndText() {
        return this.channel?.correspondent?.partner_id?.outOfOfficeDateEndText;
    },
    get hasNameSubline() {
        return super.hasNameSubline || Boolean(this.outOfOfficeDateEndText);
    },
});
