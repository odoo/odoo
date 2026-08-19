import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    get fetchRouteChatter() {
        return "/mail/chatter_fetch";
    },
});

patch(Thread, {
    async fetchMissingData(data) {
        if (!this.store.self_user?.share) {
            return super.fetchMissingData(...arguments);
        }
        await this.store.fetchStoreData("/portal/chatter_init", {
            thread_id: data.id,
            thread_model: data.model,
        });
    },
});
