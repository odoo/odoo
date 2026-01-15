import { Store } from "@mail/core/common/store_service";
import { useSequential } from "@mail/utils/common/hooks";
import { rpc } from "@web/core/network/rpc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.channels = this.makeCachedFetchData("channels_as_member");
        this.fetchSsearchConversationsSequential = useSequential();
    },
    /** @param {string} searchValue */
    async searchConversations(searchValue) {
        const data = await this.fetchSsearchConversationsSequential(async () => {
            const data = await rpc("/discuss/search", { term: searchValue });
            return data;
        });
        this.insert(data);
    },
};
patch(Store.prototype, StorePatch);
