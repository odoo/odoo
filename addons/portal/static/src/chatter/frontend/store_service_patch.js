import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    async initialize() {
        if (!this.initMessagingParams.init_messaging.channel_types) {
            this.isReady.resolve();
            return;
        }
        return super.initialize();
    },
});
