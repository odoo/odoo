import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { CalendarModel } from "@web/views/calendar/calendar_model";

export class AttendanceCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        this.employeeId = null;
    }

    /**
     * Requests are read on the clock the grid is drawn on, not on the reader's profile.
     * @override
     */
    async load(params = {}) {
        const context = params.context ?? this.meta.context;
        return super.load({
            ...params,
            context: { ...context, tz: luxon.Settings.defaultZone.name },
        });
    }

    get workingHours() {
        return this.data.workingHours || [];
    }

    /**
     * In day/week views the hourly shading (businessHours) already covers the
     * non-working days, so showing the unusual days as well shades them twice.
     * Only fall back to unusual days when there are no working hours to draw.
     * @override
     */
    get unusualDays() {
        // Day/week: the businessHours shading already covers non-working days,
        // so drawing the unusual days as well shades them twice.
        if (["day", "week"].includes(this.meta.scale) && this.workingHours.length > 0) {
            return [];
        }
        return this.data.unusualDays;
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
        if (
            ["hr.employee", "hr.employee.public"].includes(context.active_model) &&
            context.active_id
        ) {
            return context.active_id;
        }
        if (this.employeeId === null) {
            const [employee] = await this.orm.searchRead(
                "hr.employee",
                [
                    ["user_id", "=", user.userId],
                    ["company_id", "=", user.activeCompany.id],
                ],
                ["id"],
                { limit: 1 }
            );
            this.employeeId = employee?.id || false;
        }
        return this.employeeId;
    }

    async fetchUnusualDays({ range }) {
        const employeeId = await this.getEmployeeId();
        return this.orm.call(
            this.meta.resModel,
            "get_unusual_days",
            [serializeDateTime(range.start), serializeDateTime(range.end)],
            {
                context: {
                    ...this.meta.context,
                    ...(employeeId && { employee_id: employeeId }),
                },
            }
        );
    }

    async fetchWorkingHours({ range }) {
        if (!["day", "week"].includes(this.meta.scale)) {
            return [];
        }
        const employeeId = await this.getEmployeeId();
        if (!employeeId) {
            return [];
        }
        return this.orm.call(
            "hr.attendance",
            "get_working_hours_for_calendar",
            [employeeId, serializeDate(range.start), serializeDate(range.end)],
            { context: this.meta.context }
        );
    }
}
