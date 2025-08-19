import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.selectedRating;
        this.rating_stats;
    }, 

    getFetchParams() {
        const params = super.getFetchParams(...arguments);
        if (this.model !== "discuss.channel") {
            params["rating_include"] = true;
            if (this.selectedRating) {
                params["rating_value"] = this.selectedRating;
            }
        }
        return params;
    },
});
