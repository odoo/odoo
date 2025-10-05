import { DiscussSidebarCategories } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarCategories.prototype, {
    filteredThreads(threads) {
        return [...new Set([
        ...super.filteredThreads(threads),
        ...threads.filter((thread) => thread.livechat_ended_is_invited)
        ])];
    }
});
