/** @odoo-module **/

import { _t } from 'web.core';
import CalendarPopover from 'web.CalendarPopover';

export const TimeOffCalendarPopover = CalendarPopover.extend({
    template: 'hr_holidays.calendar.popover',

    init(parent, eventInfo) {
        this._super(...arguments);
        const state = this.event.extendedProps.record.state;
        this.canDelete = state && ['validate', 'refuse'].includes(state);
        this.canEdit = state !== undefined;
        this.displayFields = [];

        if (this.modelName === "hr.leave.report.calendar") {
            const duration = this.event.extendedProps.record.display_name.split(':').slice(-1);
            this.display_name = _.str.sprintf(_t("Time Off : %s"), duration);
        } else {
            this.display_name = this.event.extendedProps.record.display_name;
        }
    },
});
