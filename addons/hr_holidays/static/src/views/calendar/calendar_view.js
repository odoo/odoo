/** @odoo-module */

import { calendarView } from '@web/views/calendar/calendar_view';

import { TimeOffCalendarController } from './calendar_controller';
import { TimeOffCalendarModel } from './calendar_model';
import { TimeOffCalendarRenderer, TimeOffDashboardCalendarRenderer } from './calendar_renderer';

import { registry } from '@web/core/registry';

const TimeOffCalendarView = {
    ...calendarView,

    Controller: TimeOffCalendarController,
    Renderer: TimeOffCalendarRenderer,
    Model: TimeOffCalendarModel,

    buttonTemplate: "hr_holidays.CalendarController.controlButtons",
}

registry.category('views').add('time_off_calendar', TimeOffCalendarView);
registry.category('views').add('time_off_calendar_dashboard', {
    ...TimeOffCalendarView,
    Renderer: TimeOffDashboardCalendarRenderer,
});
