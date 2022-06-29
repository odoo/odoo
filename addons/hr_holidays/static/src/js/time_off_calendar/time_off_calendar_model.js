/** @odoo-module */

import CalendarModel from "web.CalendarModel";

export const TimeOffCalendarModel = CalendarModel.extend({
    _getFilterDomain: function() {
        const company_domain = [['user_id.company_id', 'in', this.data.context.allowed_company_ids]];
        return this._super().concat(company_domain);
    },

    calendarEventToRecord(event) {
        const data = this._super(...arguments);
        if (event.allDay) {
            let date_from = data.date_from.subtract(7, 'hours');
            date_from.add(this.getSession().getTZOffset(date_from), 'minutes');
            date_from = date_from.locale('en').format('YYYY-MM-DD HH:mm:ss');
            let date_to = data.date_to.add({
                'hour': 4,
                'minute': 59,
                'second': 59
            });
            date_to.add(this.getSession().getTZOffset(date_to), 'minutes');
            date_to = date_to.locale('en').format('YYYY-MM-DD HH:mm:ss');
            data.date_from = date_from;
            data.date_to = date_to;
        }
        return data;
    },
});
