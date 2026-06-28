import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

/** @type {import("models").Thread} */
const threadPatch = {
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
        const actionService = this.store.env.services.action;
        if (this.model === "mail.box") {
            if (this.store.discuss.isActive) {
                this.setAsDiscussThread();
            } else {
                actionService.doAction({
                    context: { active_id: `mail.box_${this.id}` },
                    tag: "mail.action_discuss",
                    type: "ir.actions.client",
                });
            }
        } else {
            actionService.doAction(this.openRecordActionRequest).catch((error) => {
                if (options?.fromMessagingMenu) {
                    this.store.inbox.highlightMessage = this.needactionMessages.at(-1);
                    actionService.doAction({
                        context: { active_id: "mail.box_inbox" },
                        tag: "mail.action_discuss",
                        type: "ir.actions.client",
                    });
                } else {
                    throw error;
                }
            });
        }
        return true;
    },
    get openRecordActionRequest() {
        return {
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
};
patch(Thread.prototype, threadPatch);
