/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class ColorField extends Component {
    static template = "web.ColorField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({
            color: this.props.value || "",
        });

        onWillUpdateProps((nextProps) => {
            this.state.color = nextProps.value || "";
        });
    }

    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
}

export const colorField = {
    component: ColorField,
    supportedTypes: ["char"],
};

registry.category("fields").add("color", colorField);
