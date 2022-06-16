/** @odoo-module **/

import viewRegistry from 'web.view_registry';

import FormController from "web.FormController";
import FormView from "web.FormView";

export const AllocationLeaveFormController = FormController.extend({
    /**
     * @override
    */
    async _applyChanges(dataPointID, changes, event) {
        const result = await this._super.apply(this, arguments);
        const formData = event.target.record.data;
        if (formData.holiday_status_id) {
            let nameSearchContext = {'holiday_status_name_get': false};
            const employee_id = formData.employee_id;
            if (employee_id) {
                nameSearchContext = {'holiday_status_name_get': true, 'employee_id': employee_id.data.id};
            }
            const nameSearch = await this._rpc({
                model: 'hr.leave.type',
                method: 'name_get',
                args: [formData.holiday_status_id.data.id],
                context: nameSearchContext,
                limit: 1
            });
            if (this.$el.find("div[name='holiday_status_id']").find('input')[0]) {
                this.$el.find("div[name='holiday_status_id']").find('input')[0].value = nameSearch[0][1];
            }
        }
        return result;
    }

});

export const AllocationLeaveFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: AllocationLeaveFormController,
    }),
});

viewRegistry.add('allocation_leave_form', AllocationLeaveFormView);
