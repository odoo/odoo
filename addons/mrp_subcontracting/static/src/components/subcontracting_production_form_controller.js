import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { _t } from "@web/core/l10n/translation";

class SubcontractingProductionFormController extends FormController {
    get actionMenuItems() {
        return {
            action: [
                {
                    key: "assign",
                    description: _t("Check Availability"),
                    callback: () => {
                        this.model.orm.call('mrp.production', 'action_assign', [this.model.root.resId]);
                        this.model.load();
                    },
                }
            ]
        };
    }
}

registry.category("views").add("subcontracting_production_form", {
    ...formView,
    Controller: SubcontractingProductionFormController,
});
