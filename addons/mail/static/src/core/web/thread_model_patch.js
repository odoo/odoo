import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";
import { Record } from "../common/record";

patch(Thread.prototype, {
    /** @type {integer|undefined} */
    recipientsCount: undefined,
    setup() {
        super.setup();
        this.recipients = Record.many("Follower");
        this.activities = Record.many("Activity", {
            sort: (a, b) => {
                if (a.date_deadline === b.date_deadline) {
                    return a.id - b.id;
                }
                return a.date_deadline < b.date_deadline ? -1 : 1;
            },
            onDelete(r) {
                this.store.env.services["mail.activity"].delete(r);
            },
        });
    },
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
});
