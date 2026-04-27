import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup();
        this.mail_activity_id = fields.One("mail.activity");
    },

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

    get isActivity() {
        return !!this.mail_activity_id;
    },

    async reuseActivity() {
        const context = {
            default_activity_type_id: this.mail_activity_id.activity_type_id.id,
            default_summary: this.mail_activity_id.summary,
            default_note: this.mail_activity_id.note,
        };
        await this.store.scheduleActivity(this.thread.model, [this.thread.id], context);
        this.thread.fetchThreadData(["activities", "messages"]);
    },
};
patch(Message.prototype, messagePatch);
