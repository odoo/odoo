import { AND, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class FollowerListView extends Record {
    static id = AND("threadModel", "threadId");
    /** @returns {import("models").FollowerListView} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {import("models").FollowerListView}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    threadId;
    /** @type {string} */
    threadModel;
    followers = Record.many("mail.followers");
    /** @type {number} */
    followersCount;

    async loadFollowers(offset = this.followers.length) {
        const res = await rpc("/mail/thread/get_followers", {
            thread_id: this.threadId,
            thread_model: this.threadModel,
            limit: 20,
            offset: offset,
        });
        this.store.insert(res);
    }
}

FollowerListView.register();
