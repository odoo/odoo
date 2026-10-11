import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patchModel } from "@mail/model/export";

export const DiscussChannelPatch = patchModel(DiscussChannel, {
    get isCallDisplayedInChatWindow() {
        return (
            super.isCallDisplayedInChatWindow &&
            (this.store.env.services.ui.isSmall || !this.store.discuss.isActive)
        );
    },
});
