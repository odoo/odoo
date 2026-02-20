import { Component, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AttendanceCalendarOverview extends Component {
    static template = "hr_attendance.AttendanceCalendarOverview";
    static props = {
        dateRange: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.floatTime = registry.category("formatters").get("float_time");
        this.state = useState({
            workedHours: 0,
            extraHours: 0,
        });
        useEffect(
            () => { this.loadData(); },
            () => [this.props.dateRange]
        );
    }

    get displayExtraHours() {
        return this.env.searchModel.context.display_extra_hours ?? false;
    }

    async loadData() {
        const { start, end } = this.props.dateRange;
        const employeeId = this.env.searchModel.context.active_id;
        const attendace_data = await this.orm.call("hr.employee", "get_attendace_data_by_employee", [employeeId, start, end]);
        this.state.workedHours = attendace_data[employeeId].worked_hours;
        this.state.extraHours = attendace_data[employeeId].overtime_hours;
    }
}
