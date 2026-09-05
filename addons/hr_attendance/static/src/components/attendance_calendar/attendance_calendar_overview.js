import { Component, proxy, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class AttendanceCalendarOverview extends Component {
    static template = "hr_attendance.AttendanceCalendarOverview";
    static props = {
        dateRange: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = proxy({
            entries: [],
        });
        useEffect(() => {
            this.loadData();
        });
    }

    formatHours(hours) {
        return `${Math.floor(Math.round(hours * 60) / 60)}h`;
    }

    formatMins(hours) {
        const m = Math.round(hours * 60) % 60;
        return m > 0 ? `${m}m` : "";
    }

    async loadData() {
        const { start, end } = this.props.dateRange;
        let employeeId = this.env.searchModel.context.active_id;
        if (!employeeId) {
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["user_id", "=", user.userId]],
                ["id"],
                { limit: 1 },
            );
            if (!employees.length) return;
            employeeId = employees[0].id;
        }
        const attendace_data = await this.orm.call(
            "hr.employee",
            "get_attendace_data_by_employee",
            [employeeId, start, end]
        );
        const data = attendace_data[employeeId];
        if (!data) return;
        this.state.entries = data.entries || [];
    }
}
