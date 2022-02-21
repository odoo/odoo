/** @odoo-module */

import CalendarModel from "web.CalendarModel";


export const TimeOffCalendarModel = CalendarModel.extend({
    _getFilterDomain: function() {
        const company_domain = [['user_id.company_id', 'in', this.data.context.allowed_company_ids]];
        return this._super().concat(company_domain);
    },
});
