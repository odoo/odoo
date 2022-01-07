/** @odoo-module **/

import { Domain } from "@web/core/domain";
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

    onChange(resId, ev) {
        const resIds = new Set(this.props.value.resIds);
        resIds[ev.target.checked ? "add" : "delete"](resId);
        this.props.update({
            operation: "REPLACE_WITH",
            resIds: [...resIds],
        });
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
    const activeField = datapoint.activeFields[fieldName];
    const context = datapoint.evalContext;
    const domain = new Domain(activeField.attrs.domain).toList(context);

    if (domain.toString() === datapoint.preloadedDataCaches[fieldName]) {
        return Promise.resolve();
    }
    datapoint.preloadedDataCaches[fieldName] = domain.toString();

    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("many2many_checkboxes", preloadMany2ManyCheckboxes);
