/** @odoo-module **/

import { _t } from "web.core";
import { TimeOffCalendarController } from "./time_off_calendar_controller";

export const TimeOffCalendarEmployeeController = TimeOffCalendarController.extend({

    _onOpenCreate() {
        this.context['default_employee_id'] = this.context.employee_id[0];
        this._super(...arguments);
    },

    _getAllocationButtonTitle() {
        return _t('New Allocation Request');
    },

    _getFormViewId() {
        return 'hr_holidays.hr_leave_allocation_view_form_manager_dashboard';
    },

    _getTimeOffContext() {
        const context = this._super(...arguments);
        context.default_employee_id = this.context.employee_id[0];
        return context;
    },

    _getAllocationContext() {
        const context = this._super(...arguments);
        context.default_employee_id = this.context.employee_id[0];
        return context;
    },

});
