import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        /** @type {string|undefined} */
        this.companyName;
        /** @type {boolean|undefined} */
        this.inPublicPage;
        /** @type {boolean|undefined} */
        this.isChannelTokenSecret;
        /** @type {boolean|undefined} */
        this.is_welcome_page_displayed;
    },
};

patch(Store.prototype, storeServicePatch);
