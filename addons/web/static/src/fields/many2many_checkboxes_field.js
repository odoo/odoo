/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyCheckboxesField extends Component {
    get items() {
        return this.props.record.specialData[this.props.name];
    }

    isSelected(item) {
        return this.props.value.resIds.includes(item[0]);
    }

    onChange() {
        /** @todo */
    }
}

Object.assign(Many2ManyCheckboxesField, {
    props: {
        ...standardFieldProps,
    },
    template: "web.Many2ManyCheckboxesField",
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("many2many_checkboxes", Many2ManyCheckboxesField);

function fetchMany2ManyCheckboxesSpecialData(datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    const domain = [];
    return datapoint.model.orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("specialData").add("many2many_checkboxes", fetchMany2ManyCheckboxesSpecialData);
