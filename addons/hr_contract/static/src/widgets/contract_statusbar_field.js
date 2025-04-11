import { registry } from "@web/core/registry";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class HrContractStatusBarField extends StatusBarField {
    
    async selectItem(item) {
        const { record } = this.props;
        if (record.resModel != 'hr.contract') {
            super.selectItem(item);
        }
        try {
            await super.selectItem(item);
        } catch (e) {
            e.data.record = record;
            throw e
        }
    }
}

export const hrContractStatusBarField = {
    ...statusBarField,
    component: HrContractStatusBarField,
    additionalClasses: ["o_field_statusbar"],
};

registry.category("fields").add("hr_contract_statusbar", hrContractStatusBarField);
