import { fields, Record } from "@mail/model/export";
import { rpc, ConnectionAbortedError } from "@web/core/network/rpc";

/**
 * Holds the follower list state owned by a single FollowerList component.
 *
 * Each view owns its loaded followers so independently rendered lists can
 * paginate without mutating shared state on the mail.thread record.
 */
export class FollowerListView extends Record {
    followers = fields.Many("mail.followers");
    /** @type {number} */
    followersCount;
    /** @type {number} */
    id;
    thread = fields.One("mail.thread");

    get isFullyLoaded() {
        return this.followers.length >= this.followersCount;
    }

    /**
     * Fetches and appends the next page of followers.
     *
     * Follower records are normalized in the global store, while their ordered
     * relation remains scoped to this view.
     *
     * @param {Object} options
     * @param {AbortSignal} options.abortSignal Signal used to cancel the RPC when
     * the component owning this view is destroyed while the request is still in flight.
     */
    loadFollowers({ abortSignal }) {
        const request = rpc("/mail/thread/get_followers", {
            thread_id: this.thread.id,
            thread_model: this.thread.model,
            offset: this.followers.length,
        });
        const abortRequest = () => request.abort();
        abortSignal.addEventListener("abort", abortRequest, { once: true });
        return request
            .then(({ follower_ids, followers_count, store_data }) => {
                this.store.insert(store_data);
                this.followersCount = followers_count ?? this.followersCount;
                this.followers.add(...follower_ids);
            })
            .catch((error) => {
                if (!(error instanceof ConnectionAbortedError)) {
                    throw error;
                }
            })
            .finally(() => abortSignal.removeEventListener("abort", abortRequest));
    }
}

FollowerListView.register();
