/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class EmployeeLineMany2Many extends X2ManyField {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    }

    async onAdd ({ context, editable }) {
        await this.props.record.model.root.save();
        const domain = await this.orm.call("hr.payslip.employees", "get_employees_domain",
            [this.props.record.resId]);
        this.props.domain = domain
        return super.onAdd({ context, editable });
    }
}


export const employeeLineMany2Many = {
    ...x2ManyField,
    component: EmployeeLineMany2Many,
};

registry.category("fields").add("employee_line_many2many", employeeLineMany2Many);
