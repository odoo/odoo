import { Component, proxy, t, useEffect, usePlugin, useProps } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { user } from "@web/core/user";
import { formatDuration } from "@web/views/fields/formatters";

export class AttendanceCalendarOverview extends Component {
    static template = "hr_attendance.AttendanceCalendarOverview";

    props = useProps({
        dateRange: t.object(),
        employeeId: t.or([t.number(), t.boolean()]).optional(),
    });

    setup() {
        this.orm = usePlugin(ORM);
        this.formatDuration = formatDuration;
        this.state = proxy({
            entries: [],
        });
        useEffect(() => {
            this.loadData();
        });
    }

    async loadData() {
        const { start, end } = this.props.dateRange;
        let employeeId = this.props.employeeId;
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
            "get_attendance_data_by_employee",
            [employeeId, start, end]
        );
        const data = attendace_data[employeeId];
        if (!data) return;
        this.state.entries = data.entries || [];
    }
}
