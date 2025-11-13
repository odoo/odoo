import { patch } from "@web/core/utils/patch";
import { composerActionsInternal } from "@mail/core/common/composer_actions";

patch(composerActionsInternal, {
    condition(component, id, action) {
        if (id === "open-full-composer" && component.env.projectSharingId) {
            return false;
        }
        return super.condition(component, id, action);
    },
});
