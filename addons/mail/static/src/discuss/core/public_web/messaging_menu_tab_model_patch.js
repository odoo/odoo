import { threadCompareRegistry } from "@mail/core/common/thread_compare";
import { MessagingMenuTab } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(MessagingMenuTab.prototype, {
    setup() {
        super.setup(...arguments);
        this.channels = fields.Many("discuss.channel", {
            inverse: "messagingMenuTabs",
            sort(c1, c2) {
                for (const fn of threadCompareRegistry.getAll()) {
                    const result = fn(c1.thread, c2.thread);
                    if (result !== undefined) {
                        return result;
                    }
                }
                if (c1.localId === c2.localId) {
                    return 0;
                }
                return c2.localId > c1.localId ? 1 : -1;
            },
        });
        this.channelsWithCounter = fields.Many("discuss.channel", {
            inverse: "messagingMenuTabsWithCounter",
        });
        /**
         * Determine if a channel should be included in this tab. Centralizes membership
         * logic to avoid scattering it across tab definitions and channel model patches.
         *
         * @type {(message: import("models").DiscussChannel) => boolean}
         */
        this.matchesChannel = () => false;
    },

    /** @override */
    _computeCounter() {
        if (this.recordType !== "discuss.channel") {
            return super._computeCounter();
        }
        const unloadedUnreadCount = this.init_counter_ids.filter((id) => {
            const channel = this.store["discuss.channel"].get(id);
            return !channel || channel.fetchChannelInfoState !== "fetched";
        }).length;
        return this.channelsWithCounter.length + unloadedUnreadCount + this.extraCounter;
    },

    _computeLoadMoreExcludeIds() {
        return this.recordType === "discuss.channel"
            ? this.channels.map((c) => c.id)
            : super._computeLoadMoreExcludeIds();
    },
});
