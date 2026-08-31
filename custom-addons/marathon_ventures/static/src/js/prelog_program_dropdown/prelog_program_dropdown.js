/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MvNativeSelectField extends Component {
    static template = "marathon_ventures.MvNativeSelectField";
    static props = {
        ...standardFieldProps,
    };

    get options() {
        return (this.props.record.fields[this.props.name].selection || []).filter(
            ([value, label]) => value !== false && value !== "" && label
        );
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    onChange(ev) {
        this.props.record.update({ [this.props.name]: ev.target.value || false });
    }
}

registry.category("fields").add("mv_native_select", {
    component: MvNativeSelectField,
    supportedTypes: ["selection"],
});
