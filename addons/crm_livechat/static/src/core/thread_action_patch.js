import { threadActionsInternal } from "@mail/core/common/thread_actions";

import { patch } from "@web/core/utils/patch";

patch(threadActionsInternal, {
    condition(component, id, action) {
        if (
            id === "create-lead" &&
            component.thread?.channel_type === "livechat" &&
            component.store.has_access_create_lead &&
            !component.isDiscussSidebarChannelActions
        ) {
            return true;
        }
        return super.condition(component, id, action);
    },
});
