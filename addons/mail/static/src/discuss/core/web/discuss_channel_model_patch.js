import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (
            !this.displayToSelf &&
            !this.isLocallyPinned &&
            this.eq(this.store.discuss.thread?.channel)
        ) {
            if (this.store.discuss.isActive) {
                const newThread =
                    this.store.discuss.channelCategory.threads.find(
                        (thread) => thread.channel.displayToSelf || thread.channel.isLocallyPinned
                    ) || this.store.inbox;
                newThread.setAsDiscussThread();
            } else {
                this.store.discuss.thread = undefined;
            }
        }
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
