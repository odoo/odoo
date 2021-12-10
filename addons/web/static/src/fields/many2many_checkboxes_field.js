/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2ManyCheckboxesField extends Component {
    get items() {
        return this.props.record.preloadedData[this.props.name];
    }

    isSelected(item) {
        return this.props.value.resIds.includes(item[0]);
    }

    onChange() {
        /** @todo */
    }
}

Object.assign(Many2ManyCheckboxesField, {
    template: "web.Many2ManyCheckboxesField",
    props: {
        ...standardFieldProps,
    },

    displayName: _lt("Checkboxes"),
    supportedTypes: ["many2many"],

    isEmpty() {
        return false;
    },
});

registry.category("fields").add("many2many_checkboxes", Many2ManyCheckboxesField);

export function preloadMany2ManyCheckboxes(orm, datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    const domain = [];
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("many2many_checkboxes", preloadMany2ManyCheckboxes);
