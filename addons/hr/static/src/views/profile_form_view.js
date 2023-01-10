/** @odoo-module */

import { registry } from "@web/core/registry";

import { formView } from "@web/views/form/form_view";
import { Record, RelationalModel } from "@web/views/basic_relational_model";

export class EmployeeProfileRecord extends Record {
    async save() {
        const dirtyFields = this.dirtyFields.map((f) => f.name);
        const isSaved = await super.save(...arguments);
        if (isSaved && dirtyFields.includes("lang")) {
            this.model.actionService.doAction("reload_context");
        }
        return isSaved;
    }
}

class EmployeeProfileModel extends RelationalModel {}
EmployeeProfileModel.Record = EmployeeProfileRecord;

registry.category("views").add("hr_employee_profile_form", {
    ...formView,
    Model: EmployeeProfileModel,
});
