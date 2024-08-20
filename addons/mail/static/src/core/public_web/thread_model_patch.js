import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";

/** @type {import("models").Thread} */
const ThreadPatch = {
    /**
     * Handle the notification of a new message based on the notification setting of the user.
     * Thread on mute:
     * 1. No longer see the unread status: the bold text disappears and the channel name fades out.
     * 2. Without sound + need action counter.
     * Thread Notification Type:
     * All messages:All messages sound + need action counter
     * Mentions:Only mention sounds + need action counter
     * Nothing: No sound + need action counter
     *
     * @param {import("models").Message} message
     */
    notifyMessageToUser(message) {
        if (this.isCorrespondentOdooBot) {
            return;
        }
        const channel_notifications =
            this.custom_notifications || this.store.settings.channel_notifications;
        if (
            !this.mute_until_dt &&
            !this.store.settings.mute_until_dt &&
            (this.channel_type !== "channel" ||
                (this.channel_type === "channel" &&
                    (channel_notifications === "all" ||
                        (channel_notifications === "mentions" &&
                            message.recipients?.includes(this.store.self)))))
        ) {
            const chatWindow = this.store.ChatWindow.get({ thread: this });
            if (!chatWindow) {
                this.store.ChatWindow.insert({ thread: this }).fold();
            }
            this.store.env.services["mail.out_of_focus"].notify(message, this);
        }
    },
};

patch(Thread.prototype, ThreadPatch);
