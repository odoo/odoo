import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

import "@mail/core/public_web/thread_model_patch";

/** @type {import("models").Thread|undefined} */
let threadToOpen;

/** @type {import("models").Thread} */
const threadPatch = {
    get isEmpty() {
        return !this.channel?.from_message_id && super.isEmpty;
    },
    async setAsDiscussThread() {
        threadToOpen = this;
        if (this.prefetching) {
            // Wait for the prefetch in flight, so the thread shows already loaded instead of
            // rendering once empty and again once it resolves.
            await this.prefetching;
            if (threadToOpen !== this) {
                return;
            }
        }
        if (this.channel && !this.channel?.self_member_id?.is_pinned) {
            this.channel.isLocallyPinned = true;
        }
        super.setAsDiscussThread(...arguments);
        const menu = this.store.messagingMenu;
        const sidebarState = this.store.discuss.sidebarState;
        if (sidebarState.activeTab?.notEq(menu.bookmarkTab)) {
            const fallback = this.store.inPublicPage ? menu.channelTab : menu.chatTab;
            sidebarState.activeTab = this.channel?.primaryMessagingMenuTab ?? fallback;
        }
    },
};
patch(Thread.prototype, threadPatch);
