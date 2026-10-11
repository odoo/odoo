import { ScheduledMessage } from "@mail/chatter/common/scheduled_message_model";
import { patchModel } from "@mail/model/export";
import { htmlToTextContentInline } from "@mail/utils/common/format";

import { _t } from "@web/core/l10n/translation";

export const ScheduledMessagePatch = patchModel(ScheduledMessage, {
    setup() {
        super.setup();
        this.textContent = this.computed(() => {
            if (!this.body) {
                return "";
            }
            return htmlToTextContentInline(this.body);
        });
    },

    // Editors of the records can delete scheduled messages
    /** @returns {boolean} */
    get deletable() {
        return this.store.self_user?.is_admin || this.thread.hasWriteAccess;
    },

    /** @returns {boolean} */
    get editable() {
        return this.store.self_user?.is_admin || this.isSelfAuthored;
    },

    /** @returns {boolean} */
    get isSelfAuthored() {
        return this.author_id.eq(this.store.self);
    },

    get isSubjectThreadName() {
        return (
            this.thread.display_name?.trim().toLowerCase() === this.subject?.trim().toLowerCase()
        );
    },

    /**
     * Cancel the scheduled message.
     */
    async cancel() {
        await this.store.env.services.orm.unlink("mail.scheduled.message", [this.id]);
        this.delete();
    },

    /**
     * Open the mail_compose_mesage form view to allow edition of the scheduled message.
     * If the message has already been sent, displays a notification instead.
     */
    async edit() {
        let action;
        try {
            action = await this.store.env.services.orm.call(
                "mail.scheduled.message",
                "open_edit_form",
                [this.id]
            );
        } catch {
            this.notifyAlreadySent();
            return;
        }
        return new Promise((resolve) =>
            this.store.env.services.action.doAction(action, { onClose: resolve })
        );
    },

    notifyAlreadySent() {
        this.store.env.services.notification.add(_t("This message has already been sent."), {
            type: "warning",
        });
    },

    /**
     * Send the scheduled message directly
     */
    async send() {
        try {
            await this.store.env.services.orm.call("mail.scheduled.message", "post_message", [
                this.id,
            ]);
        } catch {
            // already sent (by someone else or by cron)
            return;
        }
    },
});
