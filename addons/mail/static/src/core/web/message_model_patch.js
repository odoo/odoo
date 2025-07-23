import { Message } from "@mail/core/common/message_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyAll(thread) {
        return this.canForward(thread) && !this.isNote;
    },
    /** @param {import("models").Thread} thread */
    canForward(thread) {
        if (!thread) {
            return false;
        }
        return (
            !["discuss.channel", "mail.box"].includes(thread.model) &&
            ["comment", "email"].includes(this.message_type)
        );
    },
    /** @param {import("models").Thread} thread  */
    canMoveToInbox(thread) {
        if (!thread) {
            return false;
        }
        return (
            this.store.self?.main_user_id?.notification_type === "inbox" &&
            (this.store.history.eq(thread) ||
                (!this.needaction && !["discuss.channel", "mail.box"].includes(thread.model)))
        );
    },
    /** @param {import("models").Thread} thread  */
    async moveToInbox(thread) {
        await this.store.env.services.orm.silent.call("mail.message", "move_to_inbox", [[this.id]]);
        if (thread.model != "mail.box") {
            this.store.env.services.notification.add(_t("Marked as unread"), { type: "info" });
        }
    },
};
patch(Message.prototype, messagePatch);
