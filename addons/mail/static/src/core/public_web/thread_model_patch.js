import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";
import { router } from "@web/core/browser/router";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Thread} */
const threadModelPatch = {
    setup() {
        super.setup(...arguments);
        /**
         * Inverse of discuss.thread, useful to efficiently check whether this thread is the one
         * currently displayed in discuss app.
         */
        this.discussAppAsThread = fields.One("DiscussApp", { inverse: "thread" });
    },
    /** Condition for whether the conversation should become present in chat hub on new message */
    get inChathubOnNewMessage() {
        return !this.store.discuss.isActive;
    },
    get autoOpenChatWindowOnNewMessage() {
        return false;
    },
    /** @param {boolean} pushState */
    setAsDiscussThread(pushState) {
        if (pushState === undefined) {
            pushState = !this.discussAppAsThread;
        }
        this.store.discuss.thread = this;
        this.store.discuss.activeTab = !this.store.env.services.ui.isSmall
            ? "notification"
            : this.model === "mail.box"
            ? this.store.self_user?.notification_type === "inbox"
                ? "inbox"
                : "starred"
            : ["chat", "group"].includes(this.channel?.channel_type)
            ? "chat"
            : "channel";
        if (pushState) {
            this.setActiveURL();
        }
        if (
            this.store.env.services.ui.isSmall &&
            this.model !== "mail.box" &&
            !this.store.is_welcome_page_displayed
        ) {
            this.open({ focus: true });
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
    async unpin() {
        this.isLocallyPinned = false;
        if (this.discussAppAsThread) {
            router.replaceState({ active_id: undefined });
        }
        await this.store.chatHub.initPromise;
        this.channel?.chatWindow?.close();
        if (this.channel?.self_member_id?.is_pinned !== false) {
            await this.channel.pinRpc({ pinned: false });
        }
    },
    /** @param {string} body */
    async askLeaveConfirmation(body) {
        await new Promise((resolve) => {
            this.store.env.services.dialog.add(ConfirmationDialog, {
                body: body,
                confirmLabel: _t("Leave Conversation"),
                confirm: resolve,
                cancel: () => {},
            });
        });
    },
};
patch(Thread.prototype, threadModelPatch);
