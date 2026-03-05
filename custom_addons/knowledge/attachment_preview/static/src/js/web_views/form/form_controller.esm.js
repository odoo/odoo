import {FormController} from "@web/views/form/form_controller";
import {patch} from "@web/core/utils/patch";

patch(FormController.prototype, {
    onWillLoadRoot(nextConfiguration) {
        super.onWillLoadRoot(...arguments);
        const isSameThread =
            this.model.root?.resId === nextConfiguration.resId &&
            this.model.root?.resModel === nextConfiguration.resModel;
        if (!isSameThread) {
            this.env.bus.trigger("hide_attachment_preview");
        }
    },
});
