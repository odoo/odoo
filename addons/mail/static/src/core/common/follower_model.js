import { fields, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class Follower extends Record {
    static _name = "mail.followers";
    static id = "id";

    thread = fields.One("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner_id = fields.One("Persona");
    subtype_ids = fields.Many("mail.message.subtype");

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
<<<<<<< 5f8ef4b0b9278e8ad6cf9c355daf7c08fefa7297
        return this.partner_id.eq(this.store.self) ? this.thread.hasReadAccess : hasWriteAccess;
||||||| 5a1fff2cc61bd8676049879039defa3fb2a3f13d
        return this.partner.in(this.thread?.selves) ? this.thread.hasReadAccess : hasWriteAccess;
=======
        return this.partner.eq(this.thread?.effectiveSelf)
            ? this.thread.hasReadAccess
            : hasWriteAccess;
>>>>>>> 128d52d8437fff794754e730d07d0a877328b927
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
