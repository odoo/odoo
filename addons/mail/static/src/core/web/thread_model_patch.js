import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

import { rpc } from "@web/core/network/rpc";

export const threadPatch = patchModel(Thread, {
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
    async loadMoreFollowers() {
        const data = await this.store.env.services.orm.call(this.model, "message_get_followers", [
            [this.id],
            this.followers.at(-1).id,
        ]);
        this.store.insert(data);
    },
    async loadMoreRecipients() {
        const data = await this.store.env.services.orm.call(
            this.model,
            "message_get_followers",
            [[this.id], this.recipients.at(-1).id],
            { filter_recipients: true }
        );
        this.store.insert(data);
    },
    /** @override */
    open(options) {
        const res = super.open(...arguments);
        if (res) {
            return res;
        }
        return this.store.env.services.action.doAction(this.openRecordActionRequest, {
            newWindow: options?.newWindow,
        });
    },
    get openRecordActionRequest() {
        return {
            context: { highlight_message_id: this.highlightMessage?.id },
            type: "ir.actions.act_window",
            res_id: this.id,
            res_model: this.model,
            views: [[false, "form"]],
        };
    },
    async follow() {
        const data = await rpc("/mail/thread/subscribe", {
            res_model: this.model,
            res_id: this.id,
            partner_ids: [this.store.self_user?.partner_id?.id],
        });
        this.store.insert(data);
    },
});
