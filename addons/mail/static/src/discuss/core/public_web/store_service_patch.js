import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.channels = this.makeCachedFetchData({ channels_as_member: true });
    },
};
patch(Store.prototype, StorePatch);
