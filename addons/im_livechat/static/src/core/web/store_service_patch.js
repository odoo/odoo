import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storePatch = {
    setup() {
        super.setup(...arguments);
        this.livechatChannels = this.makeCachedFetchData("im_livechat.channel");
        this.livechatSelfExpertises = this.makeCachedFetchData("/im_livechat/fetch_self_expertise");
        this.has_access_livechat = false;
    },
    /**
     * @override
     */
    onStarted() {
        super.onStarted(...arguments);
        if (this.discuss.isActive && this.has_access_livechat) {
            this.livechatChannels.fetch();
            this.livechatSelfExpertises.fetch();
        }
    },
    /** @returns {boolean} Whether the livechat thread changed. */
    goToOldestUnreadLivechatThread() {
        const [oldestUnreadThread] = this.discuss.livechats
            .filter((thread) => thread.isUnread)
            .sort(
                (t1, t2) =>
                    !t2.livechat_end_dt - !t1.livechat_end_dt ||
                    compareDatetime(t1.lastInterestDt, t2.lastInterestDt) ||
                    t1.id - t2.id
            );
        if (!oldestUnreadThread) {
            return false;
        }
        if (this.discuss.isActive) {
            oldestUnreadThread.setAsDiscussThread();
            return true;
        }
        this.store.chatHub.initPromise.then(() => {
            const chatWindow = this.ChatWindow.insert({ thread: oldestUnreadThread });
            chatWindow.open({ focus: true, jumpToNewMessage: true });
        });
        return true;
    },
    get livechatStatusButtons() {
        return [
            {
                label: _t("In progress"),
                status: "in_progress",
                icon: "fa fa-comments",
            },
            {
                label: _t("Waiting for customer"),
                status: "waiting",
                icon: "fa fa-hourglass-start",
            },
            {
                label: _t("Looking for help"),
                status: "need_help",
                icon: "fa fa-lg fa-exclamation-circle",
            },
        ];
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
};
patch(Store.prototype, storePatch);
