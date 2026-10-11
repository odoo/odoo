import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.rating_avg = undefined;
        /** @type {number|undefined} */
        this.rating_count = undefined;
        /** @type {{ avg: number, total: number, percent: Object<number, number>}|undefined}*/
        this.rating_stats = undefined;
    },
});
