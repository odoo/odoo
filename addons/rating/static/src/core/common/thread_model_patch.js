import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.rating_avg = undefined;
        /** @type {number|undefined} */
        this.rating_count = undefined;
        /** @type {{ avg: number, total: number, percent: Object<number, number>}|undefined}*/
        this.rating_stats = undefined;
    },
};
patch(Thread.prototype, threadPatch);
