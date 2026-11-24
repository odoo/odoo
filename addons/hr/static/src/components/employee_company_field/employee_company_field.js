import { signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";

export class EmployeeCompanyField extends Many2OneField {
    inputReset = signal(null);

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get m2oProps() {
        this.inputReset();
        return {
            ...super.m2oProps,
            update: (value, options) => this.onUpdate(value, options),
        };
    }

    async onUpdate(value, options) {
        const record = this.props.record;
        const newCompanyId = value?.id;
        if (record.resId && newCompanyId && newCompanyId !== record.data.company_id?.id) {
            const action = await this.orm.call(
                "hr.employee",
                "action_change_company",
                [[record.resId], newCompanyId],
                { context: record.context }
            );
            if (action) {
                if (await record.save()) {
                    await this.action.doAction(action, { onClose: () => record.load() });
                }
                signal.trigger(this.inputReset);
                return;
            }
        }
        return record.update({ [this.props.name]: value }, options);
    }
}

registry.category("fields").add("hr_employee_company", {
    ...buildM2OFieldDescription(EmployeeCompanyField),
});
