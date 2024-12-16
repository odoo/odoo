import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class Follower extends Record {
    static _name = "mail.followers";
    static id = "id";
    /** @type {Object.<number, import("models").Follower>} */
    static records = {};
    /** @returns {import("models").Follower} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").Follower[] : import("models").Follower}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    thread = Record.one("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner = Record.one("Persona");

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner.eq(this.store.self) ? this.thread.hasReadAccess : hasWriteAccess;
    }

    async remove() {
        const data = await rpc("/mail/thread/unsubscribe", {
            res_model: this.thread.model,
            res_id: this.thread.id,
            partner_ids: [this.partner.id],
        });
        this.store.insert(data);
    }

    removeRecipient() {
        this.thread.recipients.delete(this);
    }
}

Follower.register();
