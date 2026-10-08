import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";
import { useSequential } from "@mail/utils/common/hooks";
import { rpc } from "@web/core/network/rpc";

export const StorePatch = patchModel(Store, {
    setup() {
        super.setup(...arguments);
        this.hasHiddenChannelsFetcher = this.makeCachedFetchData("has_hidden_channels");
        this.fetchSsearchConversationsSequential = useSequential();
        this.fetchMostPopularChannelsFetcher = this.makeCachedFetchData(
            "/mail/messaging_menu/get_most_popular_channels"
        );
        this.most_popular_channels = fields.Many("discuss.channel");
    },
    /** @param {string} searchValue */
    async searchConversations(searchValue) {
        const data = await this.fetchSsearchConversationsSequential(async () => {
            const data = await rpc("/discuss/search", { term: searchValue });
            return data;
        });
        this.insert(data);
    },
});
