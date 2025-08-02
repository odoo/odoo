import { Component, useState, useEffect } from "@odoo/owl";

import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ExtraHoursSummary extends Component {
    static template = "hr_attendance.ExtraHoursSummary";
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

    get shouldDisplay() {
        return this.env.searchModel.context.display_extra_hours;
    }

    async updateOvertimeData() {
        if (!this.shouldDisplay) {
            return;
        }
        const { context, domain } = this.env.searchModel;
        const employeeId = context.employee_id;
        const { overtime_adjustments = {}, validated_overtime = {} } =
            await this.orm.call("hr.employee", "get_overtime_data", [domain, employeeId]);
        const validatedOvertimeHours = validated_overtime[employeeId] || 0;
        const adjustmentOvertimeHours = overtime_adjustments[employeeId] || 0;
        const remainingOvertimeHours = validatedOvertimeHours + adjustmentOvertimeHours;
        this.state.totalExtraHours = this.floatTime(validatedOvertimeHours);
        this.state.totalOvertimeAdjustment = this.floatTime(adjustmentOvertimeHours);
        this.state.remainingExtraHours = this.floatTime(remainingOvertimeHours);
    }
}

export class ExtraHoursListRenderer extends ListRenderer {
    static template = "hr_attendance.ExtraHoursListRenderer";
    static components = {
        ...ListRenderer.components,
        ExtraHoursSummary
    };
};

export const extraHoursListView = {
    ...listView,
    Renderer: ExtraHoursListRenderer
};

registry.category("views").add("extra_hours_list_view", extraHoursListView);
