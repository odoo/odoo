import { Thread } from "@mail/core/common/thread_model";
import { Record } from "@mail/model/record";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /** @param {string[]} requestList */
    async fetchData(requestList) {
        if (requestList.includes("messages")) {
            this.fetchNewMessages();
        }
        const result = await this.store.env.services["mail.rpc"]("/mail/thread/data", {
            request_list: requestList,
            thread_id: this.id,
            thread_model: this.model,
        });
        this.store.Thread.insert(result, { html: true });
        return result;
    },
    async loadMoreFollowers() {
        const followers = await this.store.env.services.orm.call(
            this.model,
            "message_get_followers",
            [[this.id], this.followers.at(-1).id]
        );
        Record.MAKE_UPDATE(() => {
            for (const data of followers) {
                const follower = this.store.Follower.insert({
                    thread: this,
                    ...data,
                });
                if (follower.notEq(this.selfFollower)) {
                    this.followers.add(follower);
                }
            }
        });
    },
    async loadMoreRecipients() {
        const recipients = await this.store.env.services.orm.call(
            this.model,
            "message_get_followers",
            [[this.id], this.recipients.at(-1).id],
            { filter_recipients: true }
        );
        Record.MAKE_UPDATE(() => {
            for (const data of recipients) {
                this.recipients.add({ thread: this, ...data });
            }
        });
    },
});
