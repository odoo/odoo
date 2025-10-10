import { fields, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class Follower extends Record {
    static _name = "mail.followers";
    static id = "id";

    thread = fields.One("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner = fields.One("Persona");

    get displayName() {
        return this.partner.name || this.display_name || _t("Unnamed");
    }

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner.eq(this.thread?.effectiveSelf)
            ? this.thread.hasReadAccess
            : hasWriteAccess;
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
