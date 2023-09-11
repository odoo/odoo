/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    /** @type {integer|undefined} */
    recipientsCount: undefined,
    /** @type {Number} */
    mt_comment_id: undefined,
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.size;
    },
    /**
     * @returns {import("@mail/core/web/activity_model").Activity[]}
     */
    get activities() {
        return Object.values(this._store.Activity.records)
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
