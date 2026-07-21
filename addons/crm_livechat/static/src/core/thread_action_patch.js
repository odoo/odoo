import { patch } from "@web/core/utils/patch";
import { ThreadAction } from "@mail/core/common/thread_actions";

patch(ThreadAction.prototype, {
    _condition({ action, channel, isDiscussSidebarChannelActions, store }) {
        if (
            action.id === "create-lead" &&
            channel?.channel_type === "livechat" &&
            store.has_access_create_lead &&
            !isDiscussSidebarChannelActions
        ) {
            return true;
        }
        return super._condition(...arguments);
    },
});
