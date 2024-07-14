/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Field } from "@web/views/fields/field";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useEnv } from "@odoo/owl";

export class WorkedDaysField extends Field {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        if (!record.isWorkedDaysField) {
            record.isWorkedDaysField = true;
            const oldUpdate = record.update.bind(record);
            record.update = async (changes) => {
                if ('amount' in changes || 'quantity' in changes) {
                    await oldUpdate(changes, { save: true });
                    const wizardId = record.model.config.resId;
                    if (wizardId) {
                        const action = await this.orm.call(
                            "hr.payroll.edit.payslip.lines.wizard",
                            "recompute_worked_days_lines",
                            [wizardId]
                        );
                        await this.actionService.doAction(action);
                    }
                } else {
                    await oldUpdate(changes);
                }
            }
        }
        return props;
    }
}

export class WorkedDaysRenderer extends ListRenderer {}
WorkedDaysRenderer.components = {
    ...ListRenderer.components,
    Field: WorkedDaysField,
}

export class WorkedDaysLineOne2Many extends X2ManyField {
    async onAdd ({ context, editable }) {
        const wizardId = this.props.record.resId;
        return super.onAdd({
            context: {
                ...context,
                default_edit_payslip_lines_wizard_id: wizardId,
            },
            editable
        });
    }
}
WorkedDaysLineOne2Many.components = {
    ...X2ManyField.components,
    ListRenderer: WorkedDaysRenderer
};

export const workedDaysLineOne2Many = {
    ...x2ManyField,
    component: WorkedDaysLineOne2Many,
};

export class PayslipLineField extends Field {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.orm = useEnv().services.orm;
    }

    get fieldComponentProps() {
        const props = super.fieldComponentProps;
        const record = this.props.record;
        if (!record.isPayslipLineField) {
            record.isPayslipLineField = true;
            const oldUpdate = record.update.bind(record);
            record.update = async (changes) => {
                if ('amount' in changes || 'quantity' in changes) {
                    await oldUpdate(changes, { save: true });
                    const wizardId = record.model.config.resId;
                    if (wizardId) {
                        const line_id = record.resId;
                        const action = await this.orm.call(
                            "hr.payroll.edit.payslip.lines.wizard",
                            "recompute_following_lines",
                            [wizardId, line_id]
                        );
                        await this.actionService.doAction(action);
                    }
                } else {
                    await oldUpdate(changes);
                }
            }
        }
        return props;
    }
}
export class PayslipLineRenderer extends ListRenderer {}
PayslipLineRenderer.components = {
    ...ListRenderer.components,
    Field: PayslipLineField
}

export class PayslipLineOne2Many extends X2ManyField {
    async onAdd ({ context, editable }) {
        const wizardId = this.props.record.resId;
        return super.onAdd({
            context: {
                ...context,
                default_edit_payslip_lines_wizard_id: wizardId,
            },
            editable
        });
    }
}

PayslipLineOne2Many.components = {
    ...X2ManyField.components,
    ListRenderer: PayslipLineRenderer
};

export const payslipLineOne2Many = {
    ...x2ManyField,
    component: PayslipLineOne2Many,
};

registry.category("fields").add("payslip_line_one2many", payslipLineOne2Many);
registry.category("fields").add("worked_days_line_one2many", workedDaysLineOne2Many);
