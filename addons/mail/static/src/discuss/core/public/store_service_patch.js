import { Record } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        this.companyName;
        this.inPublicPage;
        this.isAnonymous = Record.attr(false, {
            compute() {
                // No user nor guest: self is the placeholder of the store service.
                return this.inPublicPage && this.self.id === -1;
            },
        });
        this.isChannelTokenSecret;
        this.discuss_public_thread = Record.one("Thread");
        this.shouldDisplayWelcomeViewInitially;
        this.shouldDisplayWelcomeView = Record.attr(undefined, {
            compute() {
                return this.shouldDisplayWelcomeView ?? this.shouldDisplayWelcomeViewInitially;
            },
        });
    },
};

patch(Store.prototype, storeServicePatch);
