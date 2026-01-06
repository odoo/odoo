import { patch } from "@web/core/utils/patch";
import { Cache } from "@web/core/utils/cache";
import { serializeDate } from "@web/core/l10n/dates";
import {TimeOffCalendarModel} from "@hr_holidays/views/calendar/calendar_model";


patch(TimeOffCalendarModel.prototype, {
    setup(params, services) {
        super.setup(params, services);
        this.data.optionalDays = {};
        if (this.env.isSmall) {
            this.meta.scale = "month";
        }

        this._optionalDaysCache = new Cache(
            (data) => this.fetchOptionalDays(data),
        );
    },

    async updateData(data) {
        const result = super.updateData(data);
        data.optionalDays = await this._optionalDaysCache.read(data);
        return result;
    },

    async fetchOptionalDays(data) {
        return this.orm.call("hr.employee", "get_optional_days", [
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
    },

    get optionalDays() {
        return this.data.optionalDays;
    }
});
