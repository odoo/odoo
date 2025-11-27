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
        this.displayToSelf = fields.Attr(false, {
            compute() {
                return (
                    this.self_member_id?.is_pinned ||
                    (["channel", "group"].includes(this.channel_type) &&
                        this.self_member_id &&
                        !this.parent_channel_id)
                );
            },
            onUpdate() {
                this.onPinStateUpdated();
            },
        });
        this.isDisplayInSidebar = fields.Attr(false, {
            compute() {
                return (
                    this.displayToSelf ||
                    this.isLocallyPinned ||
                    this.sub_channel_ids.some((thread) => thread.channel?.isDisplayInSidebar)
                );
            },
        });
        this.subChannelsInSidebar = fields.Many("mail.thread", {
            compute() {
                return this.sub_channel_ids?.filter((thread) => thread.channel?.isDisplayInSidebar);
            },
        });
    },
    delete() {
        this.store.env.services.bus_service.deleteChannel(this.busChannel);
        super.delete(...arguments);
    },
    get allowCalls() {
        return super.allowCalls && !this.parent_channel_id;
    },
    /** @param {string} description */
    async notifyDescriptionToServer(description) {
        this.description = description;
        return this.store.env.services.orm.call(
            "discuss.channel",
            "channel_change_description",
            [[this.id]],
            { description }
        );
    },
    get allowedToLeaveChannelTypes() {
        return ["channel", "group"];
    },
    get allowedToUnpinChannelTypes() {
        return ["chat"];
    },
    get canLeave() {
        return (
            !this.parent_channel_id &&
            this.allowedToLeaveChannelTypes.includes(this.channel_type) &&
            this.group_ids.length === 0 &&
            this.store.self_user
        );
    },
    get canUnpin() {
        return (
            this.parent_channel_id || this.allowedToUnpinChannelTypes.includes(this.channel_type)
        );
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
    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (this.self_member_id?.is_pinned) {
            this.isLocallyPinned = false;
        }
        if (!this.self_member_id?.is_pinned && !this.isLocallyPinned) {
            this.sub_channel_ids.forEach((c) => (c.isLocallyPinned = false));
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
