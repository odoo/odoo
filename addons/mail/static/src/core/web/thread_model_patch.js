import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { Record } from "../common/record";
import { compareDatetime } from "@mail/utils/common/misc";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.recipientsCount = undefined;
        this.recipients = Record.many("mail.followers");
        this.activities = Record.many("mail.activity", {
            sort: (a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id,
            onDelete(r) {
                r.remove();
            },
        });
    },
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
    computeIsDisplayed() {
        if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            return this.eq(this.store.discuss.thread);
        }
        return super.computeIsDisplayed();
    },
    async leave() {
        await this.closeChatWindow();
        super.leave(...arguments);
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
    open(options) {
        if (this.model === "discuss.channel") {
            this.store.env.services["bus_service"].addChannel(this.busChannel);
        }
        if (!this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this.openChatWindow(options);
            return;
        }
        if (this.store.env.services.ui.isSmall && this.model === "discuss.channel") {
            this.openChatWindow(options);
            return;
        }
        if (this.model !== "discuss.channel") {
            this.store.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_id: this.id,
                res_model: this.model,
                views: [[false, "form"]],
            });
            return;
        }
        super.open(...arguments);
    },
    async unpin() {
        await this.store.chatHub.initPromise;
        const chatWindow = this.store.ChatWindow.get({ thread: this });
        await chatWindow?.close();
        await super.unpin(...arguments);
    },
};
patch(Thread.prototype, threadPatch);
