import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        /** @type {{ avg: number, total: number, percent: Object<number, number>}}*/
        this.rating_stats;
    },
};
patch(Thread.prototype, threadPatch);
