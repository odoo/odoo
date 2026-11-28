import { Store } from "@mail/core/common/store_plugin";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        /** @type {boolean} */
        this.has_multi_website = undefined;
    },
};
patch(Store.prototype, storePatch);
