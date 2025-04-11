import { patch } from "@web/core/utils/patch";
import { composerActionsInternal } from "@mail/core/common/composer_actions";

patch(composerActionsInternal, {
    condition(component, id, action) {
        const requiredActions = ["send-message"];
        if (
            component.thread?.channel_type === 'ai_composer' && 
            !requiredActions.includes(id)
        ) {
            return false;
        }
        return super.condition(component, id, action);
    }
})
