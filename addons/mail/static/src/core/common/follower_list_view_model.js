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

    /** @type {number} */
    followersCount;

    selfFollower = Record.one("mail.followers");

    get followersFullyLoaded() {
        return (
            this.followersCount ===
            (this.selfFollower ? this.followers.length + 1 : this.followers.length)
        );
    }

    async loadMoreFollowers() {
        const res = await this.store.env.services.orm.call(
            this.thread_model,
            "message_get_followers",
            [[this.thread_id], 20, this.followers.length]
        );
        if (res["mail.followers"]?.length) {
            this.store.insert(res);
            this.followers.add(...res["mail.followers"]);
        }
    }

    async get_follower() {
        const res = await rpc("/mail/message/get_followers", {
            thread_id: this.thread_id,
            thread_model: this.thread_model,
            limit: 20,
            offset: this.followers.length,
            filter_recipients: false,
        });
        const { selfFollower, followersCount, data } = res;
        const followers = data?.["mail.followers"] || [];
        if (selfFollower?.["mail.followers"]?.length) {
            [this.selfFollower] = selfFollower["mail.followers"];
        }
        if (followersCount) {
            this.followersCount = followersCount;
        }
        this.followers.add(...followers);
    }
}

FollowerListView.register();
