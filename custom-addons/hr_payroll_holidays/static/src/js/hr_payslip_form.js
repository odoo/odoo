/** @odoo-module **/

import { TimeOffToDeferWarning, useTimeOffToDefer } from "@hr_payroll_holidays/views/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class PayslipFormController extends FormController {
    setup() {
        super.setup();
        this.timeOff = useTimeOffToDefer();
    }
}
PayslipFormController.template = "hr_payroll_holidays.PayslipFormController";
PayslipFormController.components = { ...PayslipFormController.components, TimeOffToDeferWarning };

registry.category("views").add("hr_payslip_form", {
    ...formView,
    Controller: PayslipFormController,
});
