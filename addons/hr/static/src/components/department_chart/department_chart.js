/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { onWillStart, useState, onWillUpdateProps, Component } from "@odoo/owl";

export class DepartmentChart extends Component {
    static template = "hr.DepartmentChart";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();

        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            hierarchy: {},
        });
        onWillStart(async () => await this.fetchHierarchy(this.props.record.resId));

        onWillUpdateProps(async (nextProps) => {
            await this.fetchHierarchy(nextProps.record.resId);
        });
    }

    async fetchHierarchy(departmentId) {
        this.state.hierarchy = await this.orm.call("hr.department", "get_department_hierarchy", [
            departmentId,
        ]);
    }

    async openDepartmentEmployees(departmentId) {
        this.action.doAction("hr.action_employee_from_department" , {
            additionalContext: {
                active_id: departmentId,
            },
        });
    }
}

export const departmentChart = {
    component: DepartmentChart,
};
registry.category("view_widgets").add("hr_department_chart", departmentChart);
