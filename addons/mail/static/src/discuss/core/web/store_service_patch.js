import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.initChannelsUnreadCounter = 0;
        this.channels = this.makeCachedFetchData({ channels_as_member: true });
    },
    onStarted() {
        super.onStarted();
        if (this.discuss.isActive) {
            this.channels.fetch();
        }
    },
};
patch(Store.prototype, StorePatch);
