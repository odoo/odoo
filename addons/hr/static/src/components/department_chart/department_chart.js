/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { onWillStart, useState, onWillUpdateProps, Component } = owl;

export class DepartmentChart extends Component {
    setup() {
        super.setup();

        this.action = useService('action');
        this.orm = useService('orm');
        this.state = useState({
            hierarchy: {}
        });
        onWillStart(async () => await this.fetchHierarchy(this.props.record.data.id));

        onWillUpdateProps(async (nextProps) => {
            await this.fetchHierarchy(nextProps.record.data.id);
        });
    }

    async fetchHierarchy(departmentId) {
        this.state.hierarchy = await this.orm.call('hr.department', 'get_department_hierarchy', [departmentId]);
    }

    openDepartmentEmployees(departmentId) {
        this.action.doAction('hr.act_employee_from_department', {
            additionalContext: {
                'active_id': departmentId,
            }
        });
    }
}
DepartmentChart.template = 'hr.DepartmentChart';
DepartmentChart.props = {
    ...standardWidgetProps,
};

registry.category("view_widgets").add("hr_department_chart", DepartmentChart);
