import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.ratingChatter = false;
        this.reviewChatter = false;
        /** @type {false|number} */
        this.selectedRating = false;
    },
});
