import { Thread } from "@mail/core/common/thread_model";
import { browser } from "@web/core/browser/browser";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setActiveURL() {
        browser.history.pushState(
            browser.history.state,
            null,
            `/discuss/channel/${this.id}${browser.location.search}`
        );
    },
});
