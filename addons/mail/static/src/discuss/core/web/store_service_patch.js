import { Store } from "@mail/core/common/store_service";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { compareDatetime } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
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
    onLinkFollowed(fromThread) {
        super.onLinkFollowed(...arguments);
        if (!this.env.isSmall && fromThread?.channel) {
            fromThread.open({ focus: false });
        }
    },
    /**
     * @override
     * @param {MouseEvent} ev
     * @param {number} id
     */
    onClickPartnerMention(ev, id) {
        this.env.services.popover.add(ev.target, AvatarCard, {
            id,
            model: "res.partner",
        });
    },
};
patch(Store.prototype, StorePatch);
