/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { useAbsenceManagementWizard } from "@hr_attendance/views/absence_wizard_hook";

console.log("loaded but not binding")
export class OvertimeRuleFormController extends FormController {

    setup() {
        console.log("🎉 OvertimeRuleFormController SETUP called!");
        super.setup()
        this.openAbsenceWizard = useAbsenceManagementWizard();
    }

    async saveRecord() {
        const result = await super.saveRecord()

        const rule = this.model.root.data;

        if (rule.quantity_comparison === "fall_behind") {
            this.openAbsenceWizard(rule.ruleset_id[0], rule.id);
        }

        return result;
    }
}

registry.category("views").add("overtime_rule_form_view", {
    ...formView,
    Controller: OvertimeRuleFormController,
});
