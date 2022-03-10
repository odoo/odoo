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
            const date_from = formData.date_from;
            const date_to = formData.date_to;
            if (employee_id && date_from) {
                nameSearchContext = {'holiday_status_name_get': true, 'employee_id': employee_id.data.id};
                nameSearchContext.default_date_from = date_from;
                nameSearchContext.default_date_to = date_to;
            }
            const nameSearch = await this._rpc({
                model: 'hr.leave.type',
                method: 'name_get',
                args: [formData.holiday_status_id.data.id],
                context: nameSearchContext,
                limit: 1
            });
            const holiday_input = this.$el.find("div[name='holiday_status_id']").find('input')[0];
            if (holiday_input) {
                holiday_input.value = nameSearch[0][1];
            }
        }
        return result;
    },

});

export const AllocationLeaveFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: AllocationLeaveFormController,
    }),
});

viewRegistry.add('allocation_leave_form', AllocationLeaveFormView);
