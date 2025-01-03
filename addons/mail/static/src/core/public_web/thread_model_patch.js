import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";
import { router } from "@web/core/browser/router";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(Thread.prototype, {
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
            if (this.model === "discuss.channel") {
                let chatWindow = this.store.ChatWindow.get({ thread: this });
                if (!chatWindow) {
                    chatWindow = this.store.ChatWindow.insert({ thread: this });
                    if (
                        this.autoOpenChatWindowOnNewMessage &&
                        !this.store.discuss.isActive &&
                        this.store.chatHub.opened.length < this.store.chatHub.maxOpened
                    ) {
                        chatWindow.open();
                    } else {
                        chatWindow.fold();
                    }
                }
            }
            this.store.env.services["mail.out_of_focus"].notify(message, this);
        }
    },
    get autoOpenChatWindowOnNewMessage() {
        return false;
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
        if (
            this.store.env.services.ui.isSmall &&
            this.model !== "mail.box" &&
            !this.store.shouldDisplayWelcomeViewInitially
        ) {
            this.open();
        }
    },

    setActiveURL() {
        const activeId =
            typeof this.id === "string" ? `mail.box_${this.id}` : `discuss.channel_${this.id}`;
        router.pushState({ active_id: activeId });
        if (
            this.store.action_discuss_id &&
            this.store.env.services.action?.currentController?.action.id ===
                this.store.action_discuss_id
        ) {
            // Keep the action stack up to date (used by breadcrumbs).
            this.store.env.services.action.currentController.action.context.active_id = activeId;
        }
    },
    open(options) {
        if (this.store.env.services.ui.isSmall) {
            this.openChatWindow(options);
            return;
        }
        this.setAsDiscussThread();
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
    askLeaveConfirmation(body) {
        return new Promise((resolve) => {
            this.store.env.services.dialog.add(ConfirmationDialog, {
                body: body,
                confirmLabel: _t("Leave Conversation"),
                confirm: resolve,
                cancel: () => {},
            });
        });
    },
    async leaveChannel({ force = false } = {}) {
        if (this.channel_type !== "group" && this.create_uid === this.store.self.userId && !force) {
            await this.askLeaveConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (this.channel_type === "group" && !force) {
            await this.askLeaveConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        this.leave();
    },
});
