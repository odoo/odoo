/** @odoo-module alias=calendar.CalendarView **/

import CalendarController from '@calendar/js/calendar_controller';
import CalendarModel from '@calendar/js/calendar_model';
import AttendeeCalendarRenderer from '@calendar/js/calendar_renderer';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';

const CalendarRenderer = AttendeeCalendarRenderer.AttendeeCalendarRenderer;

var AttendeeCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
        Renderer: CalendarRenderer,
        Controller: CalendarController,
        Model: CalendarModel,
    }),
});

viewRegistry.add('attendee_calendar', AttendeeCalendarView);

export default AttendeeCalendarView;
