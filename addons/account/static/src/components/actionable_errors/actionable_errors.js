/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/utils";

export class ActionableErrors extends Component {
    static props = { ...standardFieldProps };
    static template = "account.ActionableErrors";

    setup() {
        useRecordObserver(this.formatData.bind(this));
    }

    formatData(record) {
        const errorsField = record.data[this.props.name];
        this.errorsData = JSON.parse(JSON.stringify(errorsField));
    }

    async handleOnClick(errorData){
        this.env.model.action.doAction(errorData.action);
    }
}

export const actionableErrors = {component: ActionableErrors};
registry.category("fields").add("actionable_errors", actionableErrors);
