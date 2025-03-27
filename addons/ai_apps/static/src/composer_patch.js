import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    saveContent() {
        // no point in saving the content in an AI chat since chats are independent 
        if (this.thread?.channel_type === "ai_composer") {
            return;
        } else {
            super.saveContent();
        }
    },
    onFocusin(ev) {
        super.onFocusin();
        ev.target.select();
    }
});