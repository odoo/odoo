import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { fields } from "../common/record";
import { compareDatetime } from "@mail/utils/common/misc";
import { rpc } from "@web/core/network/rpc";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.recipientsCount = undefined;
        this.recipients = fields.Many("mail.followers");
        this.activities = fields.Many("mail.activity", {
            sort: (a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id,
            onDelete(r) {
                r.remove();
            },
        });
        /** @type {boolean} */
        this.isDisplayedInDiscussAppDesktop = fields.Attr(undefined, {
            /** @this {import("models").Thread} */
            compute() {
                if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
                    return this.eq(this.store.discuss.thread);
                }
                return false;
            },
        });
    },
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
    computeIsDisplayed() {
        return this.isDisplayedInDiscussAppDesktop || super.computeIsDisplayed();
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
        if (this.model === "mail.box") {
            if (this.store.discuss.isActive) {
                this.setAsDiscussThread();
            } else {
                this.store.env.services.action.doAction({
                    context: { active_id: `mail.box_${this.id}` },
                    tag: "mail.action_discuss",
                    type: "ir.actions.client",
                });
            }
        } else {
            this.store.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_id: this.id,
                res_model: this.model,
                views: [[false, "form"]],
            });
        }
        return true;
    },
    async unpin() {
        await this.store.chatHub.initPromise;
        const chatWindow = this.store.ChatWindow.get({ thread: this });
        await chatWindow?.close();
        await super.unpin(...arguments);
    },
    async follow() {
        const data = await rpc("/mail/thread/subscribe", {
            res_model: this.model,
            res_id: this.id,
            partner_ids: [this.store.self.id],
        });
        this.store.insert(data);
    },
};
patch(Thread.prototype, threadPatch);
