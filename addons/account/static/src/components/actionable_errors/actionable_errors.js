/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ActionableErrors extends Component {
    static props = { ...standardFieldProps };
    static template = "account.ActionableErrors";

    async handleOnClick(errorData){
        this.env.model.action.doAction(errorData.action);
    }
}

export const actionableErrors = {component: ActionableErrors};
registry.category("fields").add("actionable_errors", actionableErrors);
