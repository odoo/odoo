import { Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class FollowerListView extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").FollowerListView>} */
    static records = {};
    /** @returns {import("models").FollowerListView} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {import("models").FollowerListView|import("models").FollowerListView[]}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    /** @type {number} */
    thread_id;
    /** @type {string} */
    thread_model;
    followers = Record.many("mail.followers");
    selfFollower = Record.one("mail.followers");
    /** @type {boolean} */
    followersFullyLoaded;

    async loadFollowers(offset = this.followers.length) {
        const res = await rpc("/mail/thread/get_followers", {
            id: this.id,
            thread_id: this.thread_id,
            thread_model: this.thread_model,
            limit: 20,
            offset: offset,
        });
        this.store.insert(res);
    }
}

FollowerListView.register();
