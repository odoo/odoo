import { Store } from "@mail/core/common/store_service";
import { compareDatetime } from "@mail/utils/common/misc";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.initChannelsUnreadCounter = 0;
    },
    computeGlobalCounter() {
        if (!this["discuss.channel"]) {
            return super.computeGlobalCounter();
        }
        const channelsContribution =
            this.channels.status !== "fetched"
                ? this.initChannelsUnreadCounter
                : Object.values(this.store["discuss.channel"].records).filter(
                      (channel) =>
                          channel.displayToSelf &&
                          !channel.self_member_id?.mute_until_dt &&
                          (channel.self_member_id?.message_unread_counter ||
                              channel.message_needaction_counter)
                  ).length;
        // Needactions are already counted in the super call, but we want to discard them for channel so that there is only +1 per channel.
        const channelsNeedactionCounter = Object.values(
            this.store["discuss.channel"].records
        ).reduce((acc, channel) => acc + channel.message_needaction_counter, 0);
        return super.computeGlobalCounter() + channelsContribution + channelsNeedactionCounter;
    },
    /** @returns {import("models").DiscussChannel[]} */
    getSelfImportantChannels() {
        return this.getSelfRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
    /** @returns {import("models").DiscussChannel[]} */
    getSelfRecentChannels() {
        return Object.values(this["discuss.channel"].records)
            .filter((channel) => channel.self_member_id)
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
    /**
     * @override
     * @param {MouseEvent} ev
     * @param {number} id
     */
    onClickPartnerMention(ev, id) {
        this.env.services.popover.add(ev.target, AvatarCardPopover, {
            id,
            model: "res.partner",
        });
    },
};
patch(Store.prototype, StorePatch);
