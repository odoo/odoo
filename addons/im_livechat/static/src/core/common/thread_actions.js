import { patch } from "@web/core/utils/patch";

import { threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsInternal, {
    condition(component, id, action) {
        const visitorActions = ["fold-chat-window", "close", "restart", "call-settings"];
        if (
            component.thread?.channel_type === "livechat" &&
            component.store.self.type !== "partner" &&
            !visitorActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    },
});
