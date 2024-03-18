/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
<<<<<<< HEAD
=======
import { useRecordObserver } from "@web/model/relational_model/utils";
>>>>>>> 66076f9a3d6c9e60ba2b45e8c02467ddac830181

export class ActionableErrors extends Component {
    static props = { ...standardFieldProps };
    static template = "account.ActionableErrors";

<<<<<<< HEAD
=======
    setup() {
        useRecordObserver(this.formatData.bind(this));
    }

    formatData(record) {
        const errorsField = record.data[this.props.name];
        this.errorsData = JSON.parse(JSON.stringify(errorsField));
    }

>>>>>>> 66076f9a3d6c9e60ba2b45e8c02467ddac830181
    async handleOnClick(errorData){
        this.env.model.action.doAction(errorData.action);
    }
}

export const actionableErrors = {component: ActionableErrors};
registry.category("fields").add("actionable_errors", actionableErrors);
