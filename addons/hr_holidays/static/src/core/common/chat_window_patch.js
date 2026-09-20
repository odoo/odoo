import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    get outOfOfficeDateEndText() {
        return this.channel?.correspondent?.partner_id?.outOfOfficeDateEndText;
    },
    get displayNameFontSizeClass() {
        if (!this.outOfOfficeDateEndText) {
            return super.displayNameFontSizeClass;
        }
        return this.ui.isSmall ? "fs-5" : "fs-6";
    },
    get displayNameMarginClass() {
        return this.outOfOfficeDateEndText ? "" : super.displayNameMarginClass;
    },
    get displayNamePaddingClass() {
        return this.outOfOfficeDateEndText ? "" : super.displayNamePaddingClass;
    },
});
