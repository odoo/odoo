/* @odoo-module */

import { Store } from "@mail/core/common/store_service";
import { makeCachedFetchData } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.initChannelsUnreadCounter = 0;
        this.hasFetchedChannels = false;
        this._cachedFetchChannels = makeCachedFetchData(this, "channels_as_member");
    },
    onStarted() {
        super.onStarted();
        if (this.discuss.isActive) {
            this.fetchChannels();
        }
    },
    fetchChannels() {
        return this._cachedFetchChannels().then(() => (this.hasFetchedChannels = true));
    },
};
patch(Store.prototype, StorePatch);
