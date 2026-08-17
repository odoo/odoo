import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get inMeetingEndText() {
        return this.channel?.correspondentPartner?.inMeetingEndText;
    },
    get hasNameSubline() {
        return super.hasNameSubline || Boolean(this.inMeetingEndText);
    },
});
