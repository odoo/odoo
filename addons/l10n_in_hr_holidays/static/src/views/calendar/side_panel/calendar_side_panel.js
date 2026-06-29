import { computed } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { TimeOffCalendarSidePanel } from "@hr_holidays/views/calendar/calendar_side_panel/calendar_side_panel";

patch(TimeOffCalendarSidePanel.prototype, {
    setup() {
        super.setup();
        this.optionalHolidays = computed(() =>
          this._mapIsoToDatetimes(
            this.specialDays().optionalHolidays || []
          )
        );
    }
});
