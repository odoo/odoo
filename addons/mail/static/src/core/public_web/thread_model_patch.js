// @ts-check
/** @odoo-module native */
import { Thread } from "@mail/core/common/thread_model";
import { router } from "@web/core/browser/router";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/ui/dialog";

const log = makeLogger("mail.thread");
/** @type {Partial<import("models").Thread> & ThisType<import("models").Thread>} */
const modelPatch = {
    /** @param {import("models").Message} message */
    async notifyMessageToUser(message) {
        const channel_notifications =
            this.self_member_id?.custom_notifications ||
            this.store.settings.channel_notifications;
        if (
            !this.isMuted &&
            !this.store.self.im_status?.includes("busy") &&
            (this.channel_type !== "channel" ||
                (this.channel_type === "channel" &&
                    (channel_notifications === "all" ||
                        (channel_notifications === "mentions" &&
                            message.isSelfMentioned))))
        ) {
            log.logic("notifyMessageToUser", () => ({
                thread: this.localId,
                messageId: message.id,
                inChathub: this.inChathubOnNewMessage,
                notifyWhenOutOfFocus: this.notifyWhenOutOfFocus,
            }));
            if (this.isChannelKind && this.inChathubOnNewMessage) {
                await this.store.chatHub.initPromise;
                let chatWindow = this.store.ChatWindow.get({ thread: this });
                if (!chatWindow) {
                    log.logic("new message opens chat window", () => ({
                        thread: this.localId,
                        autoOpen: this.autoOpenChatWindowOnNewMessage,
                        opened: this.store.chatHub.opened.length,
                        maxOpened: this.store.chatHub.maxOpened,
                    }));
                    chatWindow = this.store.ChatWindow.insert({ thread: this });
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
            if (this.notifyWhenOutOfFocus) {
                this.store.env.services["mail.out_of_focus"].notify(message, this);
            }
        }
    },
    get inChathubOnNewMessage() {
        return !this.store.discuss.isActive;
    },
    get autoOpenChatWindowOnNewMessage() {
        return false;
    },
    get notifyWhenOutOfFocus() {
        return true;
    },
    /** @param {boolean} [pushState] */
    setAsDiscussThread(pushState) {
        if (pushState === undefined) {
            pushState = this.notEq(this.store.discuss.thread);
        }
        log.logic("setAsDiscussThread", () => ({
            thread: this.localId,
            previous: this.store.discuss.thread?.localId,
            pushState,
        }));
        this.store.discuss.thread = this;
        this.store.discuss.activeTab = !this.store.env.services.ui.isSmall
            ? "notification"
            : this.isMailbox
              ? this.store.selfUsesInbox
                  ? "inbox"
                  : "starred"
              : ["chat", "group"].includes(this.channel_type)
                ? "chat"
                : "channel";
        if (pushState) {
            this.setActiveURL();
        }
        if (
            this.store.env.services.ui.isSmall &&
            !this.isMailbox &&
            !this.store.is_welcome_page_displayed
        ) {
            this.open({ focus: true });
        }
    },

    setActiveURL() {
        const activeId =
            typeof this.id === "string"
                ? `mail.box_${this.id}`
                : `discuss.channel_${this.id}`;
        router.pushState({ active_id: activeId });
        if (
            this.store.action_discuss_id &&
            this.store.env.services.action?.currentController?.action.id ===
                this.store.action_discuss_id
        ) {
            this.store.env.services.action.currentController.action.context.active_id =
                activeId;
        }
    },
    async unpin() {
        log.logic("unpin", () => ({
            thread: this.localId,
            isDiscussThread: this.eq(this.store.discuss.thread),
            serverPinned: this.self_member_id?.is_pinned,
        }));
        this.isLocallyPinned = false;
        if (this.eq(this.store.discuss.thread)) {
            router.replaceState({ active_id: undefined });
        }
        if (this.isChannelKind && this.self_member_id?.is_pinned !== false) {
            await this.store.env.services.orm.silent.call(
                "discuss.channel",
                "channel_pin",
                [this.id],
                { pinned: false },
            );
        }
    },
    /**
     * @param {string} body
     * @returns {Promise<boolean>} whether the user confirmed
     */
    askLeaveConfirmation(body) {
        return new Promise((resolve) => {
            this.store.env.services.dialog.add(
                ConfirmationDialog,
                {
                    body,
                    confirmLabel: _t("Leave Conversation"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                },
                { onClose: () => resolve(false) },
            );
        });
    },
};
patch(Thread.prototype, modelPatch);
