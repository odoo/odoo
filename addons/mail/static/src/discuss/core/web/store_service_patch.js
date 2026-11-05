import { Store } from "@mail/core/common/store_plugin";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { compareDatetime } from "@mail/utils/common/misc";

import { getPopoverForTarget } from "@web/core/popover/popover";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    /** @returns {import("models").DiscussChannel[]} */
    getSelfImportantChannels() {
        return this.getSelfRecentChannels().filter((channel) => channel.importantCounter > 0);
    },
    /** @returns {import("models").DiscussChannel[]} */
    getSelfRecentChannels() {
        return [...this["discuss.channel"].records.values()]
            .filter((channel) => channel.self_member_id)
            .sort((a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id);
    },
    onLinkFollowed(fromThread) {
        super.onLinkFollowed(...arguments);
        if (!this.ui.isSmall() && fromThread?.channel) {
            fromThread.open({ focus: false });
        }
    },
    /**
     * @override
     * @param {HTMLAnchorElement} link
     * @param {import("models").Message} [message]
     */
    onClickPartnerMention(link, message) {
        // a click inside the mention does not close its card
        if (getPopoverForTarget(link)) {
            return;
        }
        this.popover.add(link, AvatarCard, {
            id: Number(link.dataset.oeId),
            message,
            model: "res.partner",
        });
    },
};
patch(Store.prototype, StorePatch);
