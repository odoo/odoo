/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "mail/core/web", {
    /** @type {integer|undefined} */
    recipientsCount: undefined,
    /** @type {Set<import("@mail/core/common/follower_model").Follower>|undefined} */
    recipients: undefined,
    /** @type {Number} */
    mt_comment_id: undefined,
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.size;
    },
    /**
     * @returns {import("@mail/core/web/activity_model").Activity[]}
     */
    setup() {
        this.recipients = new Set();
    },
    get activities() {
        return Object.values(this._store.activities)
            .filter((activity) => {
                return activity.res_model === this.model && activity.res_id === this.id;
            })
            .sort(function (a, b) {
                if (a.date_deadline === b.date_deadline) {
                    return a.id - b.id;
                }
                return a.date_deadline < b.date_deadline ? -1 : 1;
            });
    },
});
