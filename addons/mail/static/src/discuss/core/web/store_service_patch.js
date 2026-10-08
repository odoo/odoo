import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { compareDatetime } from "@mail/utils/common/misc";

export const StorePatch = patchModel(Store, {
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
        if (!this.env.services.ui.isSmall && fromThread?.channel) {
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
});
