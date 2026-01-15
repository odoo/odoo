import { fields, Record } from "@mail/model/export";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class Follower extends Record {
    static _name = "mail.followers";
    static id = "id";

    thread = fields.One("mail.thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner_id = fields.One("res.partner");
    subtype_ids = fields.Many("mail.message.subtype");

    get displayName() {
        return this.partner_id.name || this.display_name || _t("Unnamed");
    }

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner_id.eq(this.store.self_user?.partner_id)
            ? this.thread.hasReadAccess
            : hasWriteAccess;
    }

    async remove() {
        const data = await rpc("/mail/thread/unsubscribe", {
            res_model: this.thread.model,
            res_id: this.thread.id,
            partner_ids: [this.partner_id.id],
        });
        this.store.insert(data);
    }

    removeRecipient() {
        this.thread.recipients.delete(this);
    }
}

Follower.register();
