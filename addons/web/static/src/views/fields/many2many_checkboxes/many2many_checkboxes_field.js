/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class Many2ManyCheckboxesField extends Component {
    get items() {
        return this.props.record.preloadedData[this.props.name];
    }

    isSelected(item) {
        return this.props.value.currentIds.includes(item[0]);
    }

    onChange(resId, checked) {
        if (checked) {
            this.props.value.replaceWith([...this.props.value.currentIds, resId]);
        } else {
            const currentIds = [...this.props.value.currentIds];
            const index = currentIds.indexOf(resId);
            if (index > -1) {
                currentIds.splice(index, 1);
            }
            this.props.value.replaceWith(currentIds);
        }
    }
}

Many2ManyCheckboxesField.template = "web.Many2ManyCheckboxesField";
Many2ManyCheckboxesField.components = { CheckBox };
Many2ManyCheckboxesField.props = {
    ...standardFieldProps,
};
Many2ManyCheckboxesField.legacySpecialData = "_fetchSpecialRelation";

Many2ManyCheckboxesField.displayName = _lt("Checkboxes");
Many2ManyCheckboxesField.supportedTypes = ["many2many"];

Many2ManyCheckboxesField.isEmpty = () => false;

registry.category("fields").add("many2many_checkboxes", Many2ManyCheckboxesField);

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
