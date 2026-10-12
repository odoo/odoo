import { DiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommon.prototype, {
    _handleNotificationChannelDelete(channel, metadata) {
        if (channel.discussAppAsThread) {
            this.store.discuss.thread = undefined;
        }
        super._handleNotificationChannelDelete(channel, metadata);
    },
});
