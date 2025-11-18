import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.discuss_category_id = fields.One("discuss.category", {
            inverse: "channel_ids",
        });
    },
    delete() {
        this.store.env.services.bus_service.deleteChannel(this.busChannel);
        super.delete(...arguments);
    },
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
    async notifyMessageToUser(message) {
        const channel_notifications =
            this.self_member_id?.custom_notifications || this.store.settings.channel_notifications;
        if (
            !this.self_member_id?.mute_until_dt &&
            !this.store.self.im_status.includes("busy") &&
            (this.channel_type !== "channel" ||
                (this.channel_type === "channel" &&
                    (channel_notifications === "all" ||
                        (channel_notifications === "mentions" &&
                            message.partner_ids?.includes(this.store.self)))))
        ) {
            if (this.inChathubOnNewMessage) {
                await this.store.chatHub.initPromise;
                if (!this.chatWindow) {
                    const chatWindow = this.store.ChatWindow.insert({ channel: this });
                    if (
                        this.autoOpenChatWindowOnNewMessage &&
                        this.store.chatHub.opened.length < this.store.chatHub.maxOpened
                    ) {
                        chatWindow.open();
                    } else {
                        chatWindow.fold();
                    }
                }
            }
            this.store.env.services["mail.out_of_focus"].notify(message, this.thread);
        }
    },
    /** @override */
    openChannel() {
        if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this.setAsDiscussThread();
            return true;
        }
        return super.openChannel();
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
