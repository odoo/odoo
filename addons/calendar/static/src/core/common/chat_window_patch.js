import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get inMeetingEndText() {
        return this.channel?.correspondentPartner?.inMeetingEndText;
    },
    get displayNameFontSizeClass() {
        if (!this.inMeetingEndText) {
            return super.displayNameFontSizeClass;
        }
        return this.ui.isSmall ? "fs-5" : "fs-6";
    },
    get displayNameMarginClass() {
        return this.inMeetingEndText ? "" : super.displayNameMarginClass;
    },
    get displayNamePaddingClass() {
        return this.inMeetingEndText ? "" : super.displayNamePaddingClass;
    },
});
