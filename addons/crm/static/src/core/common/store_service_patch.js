import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup(...arguments);
        this.channel_types_with_create_lead = [];
    },
};

patch(Store.prototype, storeServicePatch);
