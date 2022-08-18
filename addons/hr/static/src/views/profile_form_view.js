/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';


export class EmployeeProfileFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService('action');
    }

    async save(params = {}) {
        const dirtyFields = this.model.root.dirtyFields.map((f) => f.name);
        super.save(params);

        if (dirtyFields.includes('lang')) {
            this.action.doAction("reload_context");
        }
    }
}

registry.category('views').add('hr_employee_profile_form', {
    ...formView,
    Controller: EmployeeProfileFormController,
});
