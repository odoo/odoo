/** @odoo-module **/

import CalendarView from "web.CalendarView";
import config from 'web.config';
import { TimeOffCalendarController } from "./time_off_calendar_controller";
import { TimeOffCalendarRenderer } from "./time_off_calendar_renderer";
import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";
import viewRegistry from 'web.view_registry';

export const TimeOffCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: TimeOffCalendarController,
        Renderer: TimeOffCalendarRenderer,
    }),

    /**
     * @override
     */
     init: function (viewInfo, params) {
        this._super(viewInfo, params);
        if(config.device.isMobile) {
            this.loadParams.mode = "month";
        }
    }
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
