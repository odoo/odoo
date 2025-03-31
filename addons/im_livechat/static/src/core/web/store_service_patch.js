import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.livechatChannels = this.makeCachedFetchData({ livechat_channels: true });
        this.has_access_livechat = false;
    },
    /**
     * @override
     */
    onStarted() {
        super.onStarted(...arguments);
        if (this.discuss.isActive && this.has_access_livechat) {
            this.livechatChannels.fetch();
        }
    },
    /** @returns {boolean} Whether the livechat thread changed. */
    goToOldestUnreadLivechatThread() {
        const [oldestUnreadThread] = this.discuss.livechats
            .filter((thread) => thread.isUnread)
            .sort(
                (t1, t2) => compareDatetime(t1.lastInterestDt, t2.lastInterestDt) || t1.id - t2.id
            );
        if (!oldestUnreadThread) {
            return false;
        }
        if (this.discuss.isActive) {
            oldestUnreadThread.setAsDiscussThread();
            return true;
        }
        const chatWindow = this.ChatWindow.insert({ thread: oldestUnreadThread });
        chatWindow.open();
        chatWindow.focus();
        return true;
    },
    /**
     * @override
     */
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(tab);
        if (tab === "chat" && !this.env.services.ui.isSmall) {
            threadTypes.push("livechat");
        }
        if (tab === "livechat") {
            threadTypes.push("livechat");
        }
        return threadTypes;
    },
});
