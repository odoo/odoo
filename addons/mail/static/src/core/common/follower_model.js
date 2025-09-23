import { Record } from "@mail/core/common/record";

export class Follower extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Follower>} */
    static records = {};
    /** @returns {import("models").Follower} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Follower|import("models").Follower[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    thread = Record.one("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner = Record.one("Persona");

    get displayName() {
        return this.partner.name || this.display_name;
    }

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner.eq(this.thread?.effectiveSelf)
            ? this.thread.hasReadAccess
            : hasWriteAccess;
    }

    async remove() {
        await this.store.env.services.orm.call(this.thread.model, "message_unsubscribe", [
            [this.thread.id],
            [this.partner.id],
        ]);
        this.delete();
    }

    removeRecipient() {
        this.thread.recipients.delete(this);
    }
}

Follower.register();
