import { serializeDate } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { CalendarModel } from "@web/views/calendar/calendar_model";

export class AttendanceCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        this.employeeId = null;
    }

    get workingHours() {
        return this.data.workingHours || [];
    }

    async updateData(data) {
        await super.updateData(data);
        data.workingHours = await this.fetchWorkingHours(data);
    }

    async getEmployeeId() {
        const { context } = this.meta;
        if (context.employee_id) {
            return context.employee_id;
        }
        if (context.active_model === "hr.employee" && context.active_id) {
            return context.active_id;
        }
        if (this.employeeId === null) {
            const [employee] = await this.orm.searchRead(
                "hr.employee",
                [["user_id", "=", user.userId]],
                ["id"],
                { limit: 1 }
            );
            this.employeeId = employee?.id || false;
        }
        return this.employeeId;
    }

    async fetchWorkingHours({ range }) {
        if (!["day", "week"].includes(this.meta.scale)) {
            return [];
        }
        const employeeId = await this.getEmployeeId();
        if (!employeeId) {
            return [];
        }
        return this.orm.call("hr.attendance", "get_working_hours_for_calendar", [
            employeeId,
            serializeDate(range.start),
            serializeDate(range.end),
        ]);
    }
}
