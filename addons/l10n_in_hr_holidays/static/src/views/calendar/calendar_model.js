import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { TimeOffCalendarModel } from "@hr_holidays/views/calendar/calendar_model";

patch(TimeOffCalendarModel.prototype, {
    setup(params, services) {
        super.setup(params, services);
        this.data.exceptionalDays = {};
    },

    async updateData(data) {
        await super.updateData(data);
        data.exceptionalDays = await this.fetchExceptionalDays(data);
    },

    async fetchExceptionalDays(data) {
        return this.orm.call("hr.employee", "get_exceptional_days", [
            this.employeeId,
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
    },

    get exceptionalDays() {
        return this.data.exceptionalDays;
    },
});
