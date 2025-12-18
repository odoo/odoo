import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {typeof DiscussChannel} */
const discussChannelStaticPatch = {
    /** @override */
    async getOrFetch() {
        const channel = await super.getOrFetch(...arguments);
        if (channel) {
            return channel;
        }
        // wait for restore of livechatService.savedState as channel might be inserted from there
        await this.store.isReady;
        return super.getOrFetch(...arguments);
    },
};
patch(DiscussChannel, discussChannelStaticPatch);

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.storeAsActiveLivechats = fields.One("Store", {
            compute() {
                return this.channel_type === "livechat" && !this.livechat_end_dt
                    ? this.store
                    : null;
            },
            inverse: "activeLivechats",
        });
    },
    get avatarUrl() {
        if (this.channel_type !== "livechat") {
            return super.avatarUrl;
        }
        let bestScore = -1;
        let bestMemberHistory;
        // Agents are preferred over bots, current members over former members, and higher IDs over lower IDs
        for (const memberHistory of this.livechat_channel_member_history_ids.sort(
            (a, b) => b.id - a.id
        )) {
            if (memberHistory.livechat_member_type === "visitor") {
                continue;
            }
            const score =
                (memberHistory.livechat_member_type === "agent" ? 4 : 0) +
                (memberHistory.member_id ? 2 : 0);
            if (score > bestScore) {
                bestScore = score;
                bestMemberHistory = memberHistory;
            }
        }
        return bestMemberHistory?.partner_id?.avatarUrl || super.avatarUrl;
    },
    get hasAttachmentPanel() {
        return this.channel_type !== "livechat" && super.hasAttachmentPanel;
    },
    _onDeleteChatWindow() {
        if (this.isTransient && this.channel_type === "livechat") {
            this.delete();
        }
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
