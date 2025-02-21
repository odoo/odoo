import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.initChannelsUnreadCounter = 0;
    },
    /** @returns {import("models").Thread[]} */
    getSelfImportantChannels() {
        return this.getSelfRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
    /** @returns {import("models").Thread[]} */
    getSelfRecentChannels() {
        return Object.values(this.Thread.records)
            .filter((thread) => thread.model === "discuss.channel" && thread.selfMember)
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id);
    },
    onStarted() {
        super.onStarted();
        if (this.discuss.isActive) {
            this.channels.fetch();
        }
    },
    onLinkFollowed(fromThread) {
        super.onLinkFollowed(...arguments);
        if (!this.env.isSmall && fromThread?.model === "discuss.channel") {
            fromThread.open({ focus: false });
        }
    },
};
patch(Store.prototype, StorePatch);
