/** @odoo-module **/

import { qweb as QWeb }from 'web.core';
import config from 'web.config';
import CalendarRenderer from "web.CalendarRenderer";
import { TimeOffCalendarPopover } from "./time_off_calendar_popover";

export const TimeOffPopoverRenderer = CalendarRenderer.extend({
    template: "TimeOff.CalendarView.extend",
    /**
     * We're overriding this to display the weeknumbers on the year view
     *
     * @override
     * @private
     */
    _getFullCalendarOptions() {
        const oldOptions = this._super(...arguments);
        // Parameters
        oldOptions.views.dayGridYear.weekNumbers = true;
        oldOptions.views.dayGridYear.weekNumbersWithinDays = false;
        return oldOptions;
    },

    config: Object.assign({}, CalendarRenderer.prototype.config, {
        CalendarPopover: TimeOffCalendarPopover,
    }),

    _getPopoverParams(eventData) {
        const params = this._super(...arguments);
        let calendarIcon;
        const state = eventData.extendedProps.record.state;

        if (state === 'validate') {
            calendarIcon = 'fa-calendar-check-o';
        } else if (state === 'refuse') {
            calendarIcon = 'fa-calendar-times-o';
        } else if(state) {
            calendarIcon = 'fa-calendar-o';
        }

        params.title = eventData.extendedProps.record.display_name.split(':').slice(0, -1).join(':');
        params.template = QWeb.render('hr_holidays.calendar.popover.placeholder', {
            color: this.getColor(eventData.color_index),
            calendarIcon: calendarIcon,
        });
        return params;
    },

    _render() {
        return this._super.apply(this, arguments).then(() => {
            this.$el.parent().find('.o_calendar_mini').hide();
        });
    },
    /**
     * @override
     * @private
     */
    _renderCalendar() {
        this._super(...arguments);
        const weekNumbers = this.$el.find('.fc-week-number');
        weekNumbers.each( function() {
            const weekRow = this.parentNode;
            // By default, each month has 6 weeks displayed, hide the week number if there is no days for the week
            if (!weekRow.children[1].classList.length &&
                !weekRow.children[weekRow.children.length - 1].classList.length) {
                this.innerHTML = '';
            }
        });
    },
});
