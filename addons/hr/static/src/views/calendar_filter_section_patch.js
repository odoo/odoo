import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";

patch(CalendarFilterSection.prototype, {
    /**
     * @override
     * Users without access to the employees records can only browse the public employees.
     */
    async onSearchMore(resModel, domain, request) {
        if (resModel === "hr.employee" && !(await user.hasGroup("hr.group_hr_user"))) {
            resModel = "hr.employee.public";
        }
        return super.onSearchMore(resModel, domain, request);
    },
});
