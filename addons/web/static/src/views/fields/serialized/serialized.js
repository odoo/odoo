/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class SerializedField extends Component {
    static template = "web.SerializedField";
    static props = {
        ...standardFieldProps,
    };
    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return value ? JSON.stringify(value) : "";
    }
}

export const serializedField = {
    component: SerializedField,
    displayName: _lt("Serialized"),
    supportedTypes: ["serialized"],
};

registry.category("fields").add("serialized", serializedField);
