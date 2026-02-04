import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    get notificationHidden() {
        if (
            this.store.rtc.channel?.eq(this.channel_id) &&
            this.channel_id.default_display_mode === "video_full_screen" &&
            this.store?.meetingViewOpened &&
            this.notificationType === "call"
        ) {
            return true;
        }
        return super.notificationHidden;
    },
};
patch(Message.prototype, messagePatch);
