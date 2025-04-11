import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, useEffect } from "@odoo/owl";

export class AttendanceBanner extends Component {
    static template = "hr_attendance.AttendanceBanner";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.floatTime = registry.category("formatters").get("float_time");
        this.state = useState({
            totalExtraHours: 0,
            totalOvertimeAdjustment: 0,
            remainingExtraHours: 0
        });

        useEffect(() => {
            this.updateOvertimeData();
        }, () => [this.env.searchModel.domain]);
    }

    async updateOvertimeData() {
        const employeeId = this.getEmployeeIdFromDomain();
        const overtimeData = await this.orm.call(
            "hr.employee",
            "get_overtime_data",
            [this.env.searchModel.domain, employeeId]
        );
        const overtimeAdjustment = overtimeData.overtime_adjustments
        const validatedOvertime = overtimeData.validated_overtime
        let remainingExtraHours = (validatedOvertime[employeeId] || 0) + (overtimeAdjustment[employeeId] || 0);
        this.state.totalExtraHours = validatedOvertime[employeeId] ? this.floatTime(validatedOvertime[employeeId]): 0;
        this.state.totalOvertimeAdjustment = overtimeAdjustment[employeeId] ?
                                                this.floatTime(overtimeAdjustment[employeeId]) : 0;
        this.state.remainingExtraHours = this.floatTime(remainingExtraHours);
    }

    getEmployeeIdFromDomain() {
        const domain = this.env.searchModel.domain;
        const employeeFilter = domain.find(condition => condition[0] === "employee_id");
        return employeeFilter ? employeeFilter[2] : null;
    }
}

export class AttendanceBannerListRenderer extends ListRenderer {
    static template = "hr_attendance.AttendanceBannerListRenderer";
    static components = {
        ...ListRenderer.components,
        AttendanceBanner
    };
};

export const attendanceBannerListView = {
    ...listView,
    Renderer: AttendanceBannerListRenderer
};

registry.category("views").add("attendance_banner_list_view", attendanceBannerListView);
