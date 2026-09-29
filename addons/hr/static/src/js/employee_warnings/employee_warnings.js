/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class EmployeeWarnings extends Component {
    static template = "hr.EmployeeWarnings";
    static props = standardFieldProps;

    setup() {
        this.actionService = useService("action");
    }

    async onActionClick(action) {
        if (!action) return;
        await this.actionService.doAction(action, {
            onClose: () => this.env.model.load(),
        });
    }

    get issues() {
        return Object.values(this.props.record.data[this.props.name] || {});
    }
}

export const employeeWarnings = {
    component: EmployeeWarnings,
};

registry.category("fields").add("employee_warnings", employeeWarnings);
