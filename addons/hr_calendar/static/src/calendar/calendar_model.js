import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { serializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarModel.prototype, {
    setup() {
        super.setup(...arguments)
        this.data.workingHours = {};
    },

    get workingHours() {
        return this.data.workingHours;
    },

    async updateData(data) {
        await super.updateData(...arguments)
        data.workingHours = await this.fetchWorkingHours(data);
    },

    async fetchWorkingHours(data){
        if (this.meta.scale !== "day" && this.meta.scale !== "week"){
            return [];
        }
        const attendeeFilters = data.filterSections.partner_ids;
        const activeAttendeeIds = (attendeeFilters?.filters || [])
            .filter((filter) => filter.type !== "all" && filter.value && filter.active)
            .map((filter) => filter.value);
        const allFilter = attendeeFilters?.filters.find((filter) => filter.type === "all");
        return this.orm.call("res.partner", "get_working_hours_for_all_attendees", [
            activeAttendeeIds,
            serializeDate(data.range.start),
            serializeDate(data.range.end),
            allFilter?.active
        ]);
    },
});
