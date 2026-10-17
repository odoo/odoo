import { user } from "@web/core/user";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { patch } from "@web/core/utils/patch";

patch(CalendarModel.prototype, {
    setup(params, services) {
        super.setup(params, services);
        this.isHrUser = null;
    },

    async load() {
        let hrUserProm;
        if (this.isHrUser === null) {
            hrUserProm = user
                .hasGroup("hr.group_hr_user")
                .then((result) => (this.isHrUser = result));
        }
        return Promise.all([super.load(...arguments), hrUserProm]);
    },

    async loadFilterSection(fieldName, filterInfo, previousSection) {
        if (!this.isHrUser && filterInfo?.resModel === "hr.employee") {
            filterInfo.resModel = "hr.employee.public";
        }
        return super.loadFilterSection(fieldName, filterInfo, previousSection);
    },
});
