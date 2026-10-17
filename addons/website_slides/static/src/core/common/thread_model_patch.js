import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";

export const threadPatch = patchModel(Thread, {
    setup() {
        super.setup();
        /** @type {number|undefined} */
        this.comments_count = undefined;
    },
});
