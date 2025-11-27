import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    get notificationHidden() {
        const meetingThread =
            this.thread?.model === "discuss.channel" &&
            this.thread.channel_type === "group" &&
            this.thread.default_display_mode === "video_full_screen";
        const meetingViewActive =
            meetingThread &&
            this.store?.meetingViewOpened &&
            this.store.discuss?.thread?.eq(this.thread);
        if (meetingViewActive && this.notificationType === "call") {
            return true;
        }
        return super.notificationHidden;
    },
};
patch(Message.prototype, messagePatch);
