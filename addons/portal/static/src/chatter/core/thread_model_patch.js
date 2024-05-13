import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get fetchRouteChatter() {
        return "/mail/chatter_fetch";
    },
});
