import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, asyncComputed } from "@odoo/owl";

export class DepartmentChart extends Component {
    static template = "hr.DepartmentChart";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();

        this.action = useService("action");
        this.orm = useService("orm");
        this.hierarchy = asyncComputed(
            () =>
                this.orm.call("hr.department", "get_department_hierarchy", [
                    this.props.record.resId,
                ]),
            {
                initial: {},
            }
        );
    }

    async openDepartmentEmployees(departmentId) {
        const dialogAction = await this.orm.call(
            this.props.record.resModel,
            "action_employee_from_department",
            [departmentId],
            {}
        );
        this.action.doAction(dialogAction);
    }
}

export const departmentChart = {
    component: DepartmentChart,
};
registry.category("view_widgets").add("hr_department_chart", departmentChart);
