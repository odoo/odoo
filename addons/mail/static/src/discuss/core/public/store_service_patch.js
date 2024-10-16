import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        this.companyName;
        this.inPublicPage;
        this.isChannelTokenSecret;
        this.discuss_public_thread_data;
        this.discuss_public_thread = Record.one("Thread");
        this.shouldDisplayWelcomeViewInitially;
    },
};

patch(Store.prototype, storeServicePatch);
