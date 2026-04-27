/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class BinaryFieldComission extends BinaryField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async update(changes) {
        const res = super.update(changes);
        if (changes.data) {
            await this.props.record.save();
            const recordID = this.props.record.resId;
            const action = await this.orm.call('hr.payroll.generate.warrant.payslips', 'import_employee_file', [[recordID]]);
            await this.actionService.doAction(action);
        }
        return res;
    }
}

export const binaryFieldComission = {
    ...binaryField,
    component: BinaryFieldComission,
};

registry.category("fields").add('binary_commission', binaryFieldComission);
