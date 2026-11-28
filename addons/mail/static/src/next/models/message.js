import { computed } from "@odoo/owl";
import { Model } from "@web/next/store/model";
import { mailMessageFields } from "./message_fields.generated";

/** @import { Partner } from "@web/next/models/partner" */

/** @extends {Model<typeof mailMessageFields>} */
export class Message extends Model {
    static _name = "mail.message";
    static fields = mailMessageFields;

    /** The replies that are not internal notes, oldest first. */
    publicReplies = computed(() =>
        this.child_ids()
            .filter((reply) => !reply.is_internal())
            .sort((a, b) => String(a.date()).localeCompare(String(b.date())))
    );

    get isReply() {
        return Boolean(this.parent_id());
    }

    /** The first message of the conversation this message belongs to. */
    get rootMessage() {
        /** @type {Message} */
        let message = this;
        for (let parent = message.parent_id(); parent; parent = message.parent_id()) {
            message = parent;
        }
        return message;
    }

    get authorName() {
        return this.author_id()?.name() || this.email_from() || "";
    }

    /** Everyone the message was sent to, in "to" or in copy. */
    get recipients() {
        return [...new Set([...this.partner_ids(), ...this.partner_cc_ids()])];
    }

    /**
     * @param {Partner} partner
     */
    isAuthoredBy(partner) {
        return this.author_id() === partner;
    }

    /**
     * @param {Partner} partner
     */
    isSentTo(partner) {
        return this.recipients.some((recipient) => recipient === partner);
    }

    toggleBookmark() {
        this.is_bookmarked.set(!this.is_bookmarked());
    }
}
