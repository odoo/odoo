import { Store } from "@mail/core/common/store_plugin";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean|undefined} */
        this.portalDiscussHasOrigin = undefined;
        /** @type {string|undefined} */
        this.portalDiscussNavigationUrl = undefined;
    },
});
