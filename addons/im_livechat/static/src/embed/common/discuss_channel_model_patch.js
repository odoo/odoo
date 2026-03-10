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
        this.storeAsActiveVisitorLivechats = fields.One("Store", {
            /** @this {import("models").DiscussChannel} */
            compute() {
                return this.channel_type === "livechat" &&
                    !this.livechat_end_dt &&
                    (this.self_member_id?.eq(this.livechatVisitorMember) || this.isTransient)
                    ? this.store
                    : null;
            },
            inverse: "activeVisitorLivechats",
        });
    },
    get hasAttachmentPanel() {
        return this.channel_type !== "livechat" && super.hasAttachmentPanel;
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
