/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { CheckBox } from "@web/core/checkbox/checkbox";

import { Component } from "@odoo/owl";

export class BooleanField extends Component {
    static template = "web.BooleanField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
    };

    /**
     * @param {boolean} newValue
     */
    onChange(newValue) {
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export const booleanField = {
    component: BooleanField,
    displayName: _lt("Checkbox"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
};

registry.category("fields").add("boolean", booleanField);
