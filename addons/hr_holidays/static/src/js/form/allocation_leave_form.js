/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class AllocationLeaveFormController extends FormController {
    /**
     * @override
    */
    async save() {
        const formData = this.model.root.data;
        if (formData.holiday_status_id) {
            let nameSearchContext = {'holiday_status_name_get': false};
            const employee_id = formData.employee_id;
            if (employee_id) {
                nameSearchContext = {'holiday_status_name_get': true, 'employee_id': employee_id[0]};
            }
            const nameSearch = await this.model.orm.call(
                'hr.leave.type',
                'name_get',
                [formData.holiday_status_id[0]],
                {
                    'context': nameSearchContext,
                }
            );
            const holiday_status_field = document.querySelector("div[name='holiday_status_id'] input")[0]
            if (holiday_status_field) {
                holiday_status_field.value = nameSearch[0][1];
            }
        }
        return await super.save(this, arguments);
    }
}

export const AllocationLeaveFormView = {
    ...formView,
    Controller: AllocationLeaveFormController,
}

registry.category("views").add('allocation_leave_form', AllocationLeaveFormView);
