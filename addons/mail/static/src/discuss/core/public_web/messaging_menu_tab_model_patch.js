import { threadCompareRegistry } from "@mail/core/common/thread_compare";
import { MessagingMenuTab } from "@mail/core/public_web/messaging_menu/messaging_menu_tab_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").MessagingMenuTab} */
const messagingMenuTabPatch = {
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
                return c2.id - c1.id;
            },
        });
        this.channelsWithCounter = fields.Many("discuss.channel", {
            inverse: "messagingMenuTabsWithCounter",
        });
        /**
         * Determines if a channel should be included in this tab. Centralizes membership
         * logic to avoid scattering it across tab definitions and channel model patches.
         * The server-side equivalent is resolved from `id` python side (see
         * `DiscussMessagingMenuController._get_menu_tab_domain`).
         *
         * @type {(channel: import("models").DiscussChannel) => boolean}
         */
        this.includesChannel = () => false;
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
};
patch(MessagingMenuTab.prototype, messagingMenuTabPatch);
