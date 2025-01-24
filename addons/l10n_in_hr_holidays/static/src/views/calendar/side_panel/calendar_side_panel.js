import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { TimeOffCalendarSidePanel } from "@hr_holidays/views/calendar/calendar_side_panel/calendar_side_panel";

patch(TimeOffCalendarSidePanel.prototype, {
    setup() {
        super.setup();
        this.leaveState = useState({
            ...this.leaveState,
            optionalHolidays: [],
        });
    },

    async updateSpecialDays() {
        await super.updateSpecialDays();
        const { rangeStart, rangeEnd } = this.props.model;
        const specialDays = await this._specialDaysCache.read(rangeStart, rangeEnd);
        specialDays["optionalHolidays"].forEach((optionalHoliday) => {
            optionalHoliday.start = luxon.DateTime.fromISO(optionalHoliday.start);
            optionalHoliday.end = luxon.DateTime.fromISO(optionalHoliday.end);
        });
        this.leaveState.optionalHolidays = specialDays["optionalHolidays"];
    }
})
