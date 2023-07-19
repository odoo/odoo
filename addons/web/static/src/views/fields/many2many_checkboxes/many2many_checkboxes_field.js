/** @odoo-module **/

import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";

export class Many2ManyCheckboxesField extends Component {
    static template = "web.Many2ManyCheckboxesField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
        domain: { type: Array, optional: true },
    };

    setup() {
        this.specialData = useSpecialData((orm, props) => {
            const { relation } = props.record.fields[props.name];
            return orm.call(relation, "name_search", ["", props.domain]);
        });
    }

    get items() {
        return this.specialData.data;
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
    extractProps(fieldInfo, dynamicInfo) {
        return {
            domain: dynamicInfo.domain(),
        };
    },
};

registry.category("fields").add("many2many_checkboxes", many2ManyCheckboxesField);

export function preloadMany2ManyCheckboxes(orm, record, fieldName, { domain }) {
    const field = record.fields[fieldName];
    return orm.call(field.relation, "name_search", ["", domain]);
}
