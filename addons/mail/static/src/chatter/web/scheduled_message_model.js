import { Record } from "@mail/core/common/record";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";

export class ScheduledMessage extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").ScheduledMessage>} */
    static records = {};
    /** @returns {import("models").ScheduledMessage} */
    static get(data) {
        return super.get(data);
    }
    /** @type {number} */
    id;
    attachment_ids = Record.many("Attachment");
    author = Record.one("Persona");
    body = Record.attr("", { html: true });
    /** @type {boolean} */
    composition_batch;
    /** @type {luxon.DateTime} */
    scheduled_date = Record.attr(undefined, { type: "datetime" });
    /** @type {boolean} */
    is_note;
    textContent = Record.attr(false, {
        compute() {
            if (!this.body) {
                return "";
            }
            return htmlToTextContentInline(this.body);
        },
    });
    thread = Record.one("Thread");
    // Editors of the records can delete scheduled messages
    get deletable() {
        return this.store.self.isAdmin || this.thread.hasWriteAccess;
    }

    get editable() {
        return this.store.self.isAdmin || this.isSelfAuthored;
    }

    get isSelfAuthored() {
        return this.author.eq(this.store.self);
    }

    get isSubjectThreadName() {
        return this.thread.name?.trim().toLowerCase() === this.subject?.trim().toLowerCase();
    }

    /**
     * Cancel the scheduled message.
     */
    async cancel() {
        await this.store.env.services.orm.unlink("mail.scheduled.message", [this.id]);
        this.delete();
    }

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
                [this.id],
            );
        } catch {
            this.notifyAlreadySent();
            return;
        }
        return new Promise((resolve) =>
            this.store.env.services.action.doAction(action, { onClose: resolve }),
        );
    }

    notifyAlreadySent() {
        this.store.env.services.notification.add(_t("This message has already been sent."), {
            type: "warning",
        });
    }

    /**
     * Send the scheduled message directly
     */
    async send() {
        try {
            await this.store.env.services.orm.call("mail.scheduled.message", "post_message", [this.id]);
        } catch {
            // already sent (by someone else or by cron)
            return;
        }
    }
}

ScheduledMessage.register();
