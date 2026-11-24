import { DiscussCoreCommonPlugin } from "@mail/discuss/core/common/discuss_core_common_plugin";
import { patch } from "@web/core/utils/patch";

patch(DiscussCoreCommonPlugin.prototype, {
    _handleNotificationChannelDelete(channel, metadata) {
        if (channel.discussAppAsThread) {
            this.store.discuss.thread = undefined;
        }
        super._handleNotificationChannelDelete(channel, metadata);
    },
});
