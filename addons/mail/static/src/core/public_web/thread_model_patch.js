import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";
import { Record } from "@mail/core/common/record";
import { router } from "@web/core/browser/router";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.discussAppCategory = Record.one("DiscussAppCategory", {
            compute() {
                return this._computeDiscussAppCategory();
            },
        });
    },

    _computeDiscussAppCategory() {
        if (["group", "chat"].includes(this.channel_type)) {
            return this.store.discuss.chats;
        }
        if (this.channel_type === "channel" && !this.owner_id) {
            return this.store.discuss.channels;
        }
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
    /** @param {boolean} pushState */
    setAsDiscussThread(pushState) {
        if (pushState === undefined) {
            pushState = this.notEq(this.store.discuss.thread);
        }
        this.store.discuss.thread = this;
        this.store.discuss.activeTab =
            !this.store.env.services.ui.isSmall || this.model === "mail.box"
                ? "main"
                : ["chat", "group"].includes(this.channel_type)
                ? "chat"
                : "channel";
        if (pushState) {
            this.setActiveURL();
        }
    },

    setActiveURL() {
        const activeId =
            typeof this.id === "string" ? `mail.box_${this.id}` : `discuss.channel_${this.id}`;
        router.pushState({ active_id: activeId });
    },
    open(options) {
        if (this.store.env.services.ui.isSmall) {
            this.openChatWindow(options);
            return;
        }
        super.open();
    },
    async unpin() {
        this.isLocallyPinned = false;
        if (this.eq(this.store.discuss.thread)) {
            router.replaceState({ active_id: undefined });
        }
        if (this.model === "discuss.channel" && this.is_pinned) {
            return this.store.env.services.orm.silent.call(
                "discuss.channel",
                "channel_pin",
                [this.id],
                { pinned: false }
            );
        }
    },
});
