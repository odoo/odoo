/* @odoo-module */

import { patch } from 'web.utils';
import { TimeOffCard } from '@hr_holidays/dashboard/time_off_card';

patch(TimeOffCard.prototype, "hr_holidays_attendance.TimeOffCard", {
    show_remaining() {
        return this._super() || this.props.data.overtime_deductible;
    }
});
