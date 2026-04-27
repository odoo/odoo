/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const WARNING_TYPE_ORDER = ["danger", "warning", "info"];

export class ActionableWarnings extends Component {
    static props = { errorData: {type: Object} };
    static template = "l10n_ch_hr_payroll_elm_transmission.ActionableWarnings";

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    get errorData() {
        return this.props.errorData;
    }

    async handleOnClick(errorData){
        return this.actionService.doAction(errorData.action);
    }

    get sortedActionableWarnings() {
        return this.errorData && Object.fromEntries(
            Object.entries(this.errorData).sort(
                (a, b) =>
                    WARNING_TYPE_ORDER.indexOf(a[1]["level"] || "warning") -
                    WARNING_TYPE_ORDER.indexOf(b[1]["level"] || "warning"),
            ),
        );
    }
}

export class ActionableWarningsField extends ActionableWarnings {
    static props = { ...standardFieldProps };

    get errorData() {
        return this.props.record.data[this.props.name];
    }
}

export const actionableWarningsField = {component: ActionableWarningsField};
registry.category("fields").add("actionable_warnings", actionableWarningsField);
