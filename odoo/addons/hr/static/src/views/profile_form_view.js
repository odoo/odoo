/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formView } from "@web/views/form/form_view";

export class EmployeeProfileController extends formView.Controller {
    setup() {
        super.setup();
        this.action = useService("action");
        this.mustReload = false;
    }

    onWillSaveRecord(record, changes) {
        this.mustReload = "lang" in changes;
    }

    async onRecordSaved(record) {
        await super.onRecordSaved(...arguments);
        if (this.mustReload) {
            this.mustReload = false;
            return this.action.doAction("reload_context");
        }
    }
}

registry.category("views").add("hr_employee_profile_form", {
    ...formView,
    Controller: EmployeeProfileController,
});
