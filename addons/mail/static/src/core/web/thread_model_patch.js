import { Thread } from "@mail/core/common/thread_model";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { Record } from "../common/record";

patch(Thread.prototype, {
    /** @type {integer|undefined} */
    recipientsCount: undefined,
    setup() {
        super.setup();
        this.recipients = Record.many("Follower");
        this.activities = Record.many("Activity", {
            sort: (a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id,
            onDelete(r) {
                this._store.env.services["mail.activity"].delete(r);
            },
        });
    },
    get recipientsFullyLoaded() {
        return this.recipientsCount === this.recipients.length;
    },
});
