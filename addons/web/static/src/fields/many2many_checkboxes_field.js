/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { CheckBox } from "@web/core/checkbox/checkbox";
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

    onChange(resId, checked) {
        const resIds = new Set(this.props.value.resIds);
        resIds[checked ? "add" : "delete"](resId);
        this.props.update({
            operation: "REPLACE_WITH",
            resIds: [...resIds],
        });
    }
}

Many2ManyCheckboxesField.components = { CheckBox };
Many2ManyCheckboxesField.template = "web.Many2ManyCheckboxesField";
Many2ManyCheckboxesField.props = {
    ...standardFieldProps,
};
Many2ManyCheckboxesField.displayName = _lt("Checkboxes");
Many2ManyCheckboxesField.supportedTypes = ["many2many"];
Many2ManyCheckboxesField.isEmpty = () => false;

registry.category("fields").add("many2many_checkboxes", Many2ManyCheckboxesField);

export function preloadMany2ManyCheckboxes(orm, datapoint, fieldName) {
    const field = datapoint.fields[fieldName];
    const context = datapoint.evalContext;
    const domain = datapoint.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("many2many_checkboxes", preloadMany2ManyCheckboxes);
