/* @odoo-module */

import { Thread } from "@mail/core/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, "mail/web", {
    foldStateCount: 0,
    /**
     * @returns {import("@mail/web/activity/activity_model").Activity[]}
     */
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
