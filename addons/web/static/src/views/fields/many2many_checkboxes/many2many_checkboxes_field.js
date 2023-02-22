/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class Many2ManyCheckboxesField extends Component {
    static template = "web.Many2ManyCheckboxesField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
    };

    get items() {
        return this.props.record.preloadedData[this.props.name];
    }

    isSelected(item) {
        return this.props.record.data[this.props.name].currentIds.includes(item[0]);
    }

    onChange(resId, checked) {
        if (checked) {
            this.props.record.data[this.props.name].replaceWith([
                ...this.props.record.data[this.props.name].currentIds,
                resId,
            ]);
        } else {
            const currentIds = [...this.props.record.data[this.props.name].currentIds];
            const index = currentIds.indexOf(resId);
            if (index > -1) {
                currentIds.splice(index, 1);
            }
            this.props.record.data[this.props.name].replaceWith(currentIds);
        }
    }
}

export const many2ManyCheckboxesField = {
    component: Many2ManyCheckboxesField,
    displayName: _lt("Checkboxes"),
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    legacySpecialData: "_fetchSpecialRelation",
};

registry.category("fields").add("many2many_checkboxes", many2ManyCheckboxesField);

export function preloadMany2ManyCheckboxes(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("many2many_checkboxes", {
    loadOnTypes: ["many2many"],
    preload: preloadMany2ManyCheckboxes,
});
