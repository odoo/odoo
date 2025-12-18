import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.appAsUnreadChannels = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "channel" && this.isUnread ? this.store.discuss : null;
            },
        });
        this.categoryAsChannelWithCounter = fields.One("DiscussAppCategory", {
            compute() {
                return this.isDisplayInSidebar && this.importantCounter > 0
                    ? this.discussAppCategory
                    : null;
            },
        });
        this.discussAppCategory = fields.One("DiscussAppCategory", {
            compute() {
                if (this.self_member_id?.is_favorite) {
                    return this.store.discuss.favoriteCategory;
                }
                if (this.parent_channel_id) {
                    return;
                }
                if (this.discuss_category_id) {
                    return this.discuss_category_id.appCategory;
                }
                // channel_type based categorization (including overrides) comes last
                return this._computeDiscussAppCategory();
            },
        });
        this.discuss_category_id = fields.One("discuss.category", {
            inverse: "channel_ids",
        });
        this.isDisplayInSidebar = fields.Attr(false, {
            compute() {
                return this._computeIsDisplayInSidebar();
            },
        });
        this.isLocallyPinned = fields.Attr(false, {
            onUpdate() {
                this.onPinStateUpdated();
            },
        });
        this.subChannelsInSidebar = fields.Many("discuss.channel", {
            compute() {
                return this.sub_channel_ids.filter((channel) => channel.isDisplayInSidebar);
            },
        });
    },
    _computeCanHide() {
        return Boolean(super._computeCanHide() || this?.isLocallyPinned);
    },
    _computeDiscussAppCategory() {
        if (["group", "chat"].includes(this.channel_type)) {
            return this.store.discuss.chatCategory;
        }
        if (this.channel_type === "channel") {
            return this.store.discuss.channelCategory;
        }
    },
    _computeIsDisplayInSidebar() {
        return (
            this.discussAppAsThread ||
            this.self_member_id?.is_pinned ||
            this.isLocallyPinned ||
            this.sub_channel_ids.some((thread) => thread.channel?.isDisplayInSidebar)
        );
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
        if (!this.self_member_id?.is_pinned && !this.isLocallyPinned && this.discussAppAsThread) {
            if (this.store.discuss.isActive) {
                const newChannel =
                    this.store.discuss.channelCategory.channels.find(
                        (channel) => channel.self_member_id?.is_pinned || channel.isLocallyPinned
                    ) || this.store.inbox;
                if (newChannel) {
                    newChannel.setAsDiscussThread();
                } else {
                    this.store.discuss.thread = undefined;
                }
            } else {
                this.store.discuss.thread = undefined;
            }
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
    get shouldSubscribeToBusChannel() {
        return super.shouldSubscribeToBusChannel || this.isLocallyPinned;
    },
    /** @override */
    async _unpinExecute() {
        await super._unpinExecute();
        if (!this.exists()) {
            return;
        }
        this.isLocallyPinned = false;
    },
    /** @override */
    async _unpinRegisterUndos(undos) {
        await super._unpinRegisterUndos(undos); // reset is_pinned first
        if (this.discussAppAsThread) {
            undos.push(() => this.setAsDiscussThread());
        }
        if (this.isLocallyPinned) {
            undos.push(() => (this.isLocallyPinned = true));
        }
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
