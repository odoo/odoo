/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const WARNING_TYPE_ORDER = ["danger", "warning", "info"];

export class ActionableErrors extends Component {
    static props = { errorData: {type: Object} };
    static template = "account.ActionableErrors";

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    get errorData() {
        return this.props.errorData;
    }

    async handleOnClick(errorData){
        if (errorData.action?.view_mode) {
            // view_mode is not handled JS side
            errorData.action['views'] = errorData.action.view_mode.split(',').map(mode => [false, mode]);
            delete errorData.action['view_mode'];
        }
        this.env.model.action.doAction(errorData.action);
    }

    get sortedActionableErrors() {
        return this.errorData && Object.fromEntries(
            Object.entries(this.errorData).sort(
                (a, b) =>
                    WARNING_TYPE_ORDER.indexOf(a[1]["level"] || "warning") -
                    WARNING_TYPE_ORDER.indexOf(b[1]["level"] || "warning"),
            ),
        );
    }
}

export class ActionableErrorsField extends ActionableErrors {
    static props = { ...standardFieldProps };

    get errorData() {
        return this.props.record.data[this.props.name];
    }
}

export const actionableErrorsField = {component: ActionableErrorsField};
registry.category("fields").add("actionable_errors", actionableErrorsField);
