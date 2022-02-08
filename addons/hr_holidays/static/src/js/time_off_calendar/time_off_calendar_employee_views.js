/** @odoo-module **/

import { TimeOffCalendarEmployeeController } from "./time_off_calendar_employee_controller";
import { TimeOffCalendarView } from "./time_off_calendar_views";
import viewRegistry from 'web.view_registry';

export const TimeOffCalendarEmployeeView = TimeOffCalendarView.extend({
    config: Object.assign({}, TimeOffCalendarView.prototype.config, {
        Controller: TimeOffCalendarEmployeeController,
    }),
});

viewRegistry.add('time_off_employee_calendar', TimeOffCalendarEmployeeView);
