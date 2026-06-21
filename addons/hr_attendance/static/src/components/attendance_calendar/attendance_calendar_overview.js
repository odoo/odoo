import { useLayoutEffect } from "@web/owl2/utils";
import { Component, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class AttendanceCalendarOverview extends Component {
    static template = "hr_attendance.AttendanceCalendarOverview";
    static props = {
        dateRange: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.floatTime = registry.category("formatters").get("float_time");
        this.state = proxy({
            workedHours: 0,
            extraHours: 0,
        });
        useLayoutEffect(
            () => {
                this.loadData();
            },
            () => [this.props.dateRange]
        );
    }

    get displayExtraHours() {
        return this.env.searchModel.context.display_extra_hours ?? false;
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
        this.state.workedHours = data.worked_hours;
        this.state.extraHours = data.overtime_hours;
    }
}
