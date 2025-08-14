import { patch } from "@web/core/utils/patch";
import { ThreadAction } from "@mail/core/common/thread_actions";

patch(ThreadAction.prototype, {
    _condition({ action, owner, store, thread }) {
        if (
            action.id === "create-lead" &&
            thread?.channel_type === "livechat" &&
            store.has_access_create_lead &&
            !owner.isDiscussSidebarChannelActions
        ) {
            return true;
        }
        return super._condition(...arguments);
    },
});
