import { Record } from "@mail/core/common/record";
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
        this.discuss_public_thread = Record.one("Thread");
        /** @type {boolean|undefined} */
        this.shouldDisplayWelcomeViewInitially;
    },
};

patch(Store.prototype, storeServicePatch);
