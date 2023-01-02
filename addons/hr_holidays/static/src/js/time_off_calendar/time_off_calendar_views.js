/** @odoo-module **/

import CalendarModel from "web.CalendarModel";
import CalendarView from "web.CalendarView";
import config from 'web.config';
import { TimeOffCalendarController } from "./time_off_calendar_controller";
import { TimeOffCalendarRenderer } from "./time_off_calendar_renderer";
import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";
import viewRegistry from 'web.view_registry';

export const TimeOffCalendarModel = CalendarModel.extend({
    calendarEventToRecord(event) {
        const res = this._super(...arguments);
        if (['day', 'week'].includes(this.data.scale)) {
            const { date_from, date_to } = this._getTimeOffDates(event.start.clone());

            res['date_from'] = date_from;
            res['date_to'] = date_to;
        }

        return res;
    },

    _getTimeOffDates(date_from) {
        date_from.set({
            'hour': 0,
            'minute': 0,
            'second': 0
        });
        let date_to = date_from.clone().set({
            'hour': 23,
            'minute': 59,
            'second': 59
        });

        date_from.subtract(this.getSession().getTZOffset(date_from), 'minutes');
        date_from = date_from.locale('en').format('YYYY-MM-DD HH:mm:ss');
        date_to.subtract(this.getSession().getTZOffset(date_to), 'minutes');
        date_to = date_to.locale('en').format('YYYY-MM-DD HH:mm:ss');

        return {
            date_from,
            date_to,
        }
    },
});

export const TimeOffCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: TimeOffCalendarController,
        Renderer: TimeOffCalendarRenderer,
        Model: TimeOffCalendarModel,
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
        Model: TimeOffCalendarModel,
    }),
});

viewRegistry.add('time_off_calendar', TimeOffCalendarView);
viewRegistry.add('time_off_calendar_all', TimeOffCalendarAllView);
