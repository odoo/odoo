import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        this.has_access_create_lead = false;
    },
};
patch(Store.prototype, storePatch);
