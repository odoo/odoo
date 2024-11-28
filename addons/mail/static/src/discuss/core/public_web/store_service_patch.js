import { Store } from "@mail/core/common/store_service";
import { useSequential } from "@mail/utils/common/hooks";
import { rpc } from "@web/core/network/rpc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.fetchSsearchConversationsSequential = useSequential();
    },
    getDiscussSidebarCategoryCounter(categoryId) {
        return this.DiscussAppCategory.get({ id: categoryId }).threads.reduce((acc, channel) => {
            if (categoryId === "channels") {
                return channel.message_needaction_counter > 0 ? acc + 1 : acc;
            } else {
                return channel.selfMember?.message_unread_counter > 0 ? acc + 1 : acc;
            }
        }, 0);
    },
    async searchConversations(searchValue) {
        const data = await this.fetchSsearchConversationsSequential(async () => {
            const data = await rpc("/discuss/search", { term: searchValue });
            return data;
        });
        this.insert(data);
    },
};
patch(Store.prototype, StorePatch);
