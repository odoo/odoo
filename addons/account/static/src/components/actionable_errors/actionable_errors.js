/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const WARNING_TYPE_ORDER = ["danger", "warning", "info"];

export class ActionableErrors extends Component {
    static props = { ...standardFieldProps };
    static template = "account.ActionableErrors";

    async handleOnClick(errorData){
        this.env.model.action.doAction(errorData.action);
    }

    get sortedActionableErrors() {
        const data = this.props.record.data[this.props.name];
        return Object.fromEntries(
            Object.entries(data).sort(
                (a, b) =>
                    WARNING_TYPE_ORDER.indexOf(a[1]["level"] || "warning") -
                    WARNING_TYPE_ORDER.indexOf(b[1]["level"] || "warning"),
            ),
        );
    }
}

export const actionableErrors = {component: ActionableErrors};
registry.category("fields").add("actionable_errors", actionableErrors);
