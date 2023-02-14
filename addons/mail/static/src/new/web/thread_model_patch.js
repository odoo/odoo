/* @odoo-module */

import { Thread } from "@mail/new/core/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "mail/web", {
    /**
     * @returns {import("@mail/new/web/activity/activity_model").Activity[]}
     */
    get activities() {
        return Object.values(this._store.activities).filter((activity) => {
            return activity.res_model === this.model && activity.res_id === this.id;
        });
    },
});
