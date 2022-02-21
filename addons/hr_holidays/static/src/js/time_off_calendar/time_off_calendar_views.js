/** @odoo-module **/

import CalendarView from "web.CalendarView";
import { TimeOffCalendarController } from "./time_off_calendar_controller";
import { TimeOffCalendarModel } from "./time_off_calendar_model";
import { TimeOffCalendarRenderer } from "./time_off_calendar_renderer";
import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";
import viewRegistry from 'web.view_registry';

export const TimeOffCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: TimeOffCalendarController,
        Model: TimeOffCalendarModel,
        Renderer: TimeOffCalendarRenderer,
    }),
});

/**
 * Calendar shown in the "Everyone" menu
 */
export const TimeOffCalendarAllView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: TimeOffCalendarController,
        Renderer: TimeOffPopoverRenderer,
    }),
});

viewRegistry.add('time_off_calendar', TimeOffCalendarView);
viewRegistry.add('time_off_calendar_all', TimeOffCalendarAllView);
