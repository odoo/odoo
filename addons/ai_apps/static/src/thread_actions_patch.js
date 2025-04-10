import { patch } from "@web/core/utils/patch";
import { threadActionsInternal } from "@mail/core/common/thread_actions";

patch(threadActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ["close", "fold-chat-window", "expand-discuss"];
        if (
            component.thread?.channel_type === 'ai_composer' && 
            !requiredActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    }
})
