import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class IrFiltersFormController extends FormController {
    isLeavingFilter() {
        const userIds = this.model.root.data.user_ids;
        return (
            userIds.resIds.includes(user.userId) &&
            !userIds.currentIds.includes(user.userId) &&
            userIds.currentIds.length > 0
        );
    }

    async beforeVisibilityChange() {
        if (!this.isLeavingFilter()) {
            return super.beforeVisibilityChange();
        }
    }

    async save(params = {}) {
        // without reload, the caller (e.g. beforeLeave) is already navigating away
        if (params.reload === false || !this.isLeavingFilter()) {
            return super.save(params);
        }
        const saved = await super.save({ ...params, reload: false });
        if (saved) {
            this.env.config.historyBack();
        }
        return saved;
    }
}

registry
    .category("views")
    .add("ir_filters_form", { ...formView, Controller: IrFiltersFormController });
