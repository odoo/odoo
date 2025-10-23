import { MailFollowers } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(MailFollowers.prototype, {
    setup() {
        super.setup(...arguments);
        this.thread = fields.One("mail.thread");
    },
    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner_id.eq(this.store.self_user?.partner_id)
            ? this.thread.hasReadAccess
            : hasWriteAccess;
    },
    async remove() {
        const data = await rpc("/mail/thread/unsubscribe", {
            res_model: this.thread.model,
            res_id: this.thread.id,
            partner_ids: [this.partner_id.id],
        });
        this.store.insert(data);
    },
    removeRecipient() {
        this.thread.recipients.delete(this);
    },
});
