/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { evalDomain } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

export class ColorField extends Component {
    static template = "web.ColorField";
    static props = {
        ...standardFieldProps,
        readonlyFromModifiers: { type: Array | Boolean, optional: true },
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
        return evalDomain(this.props.readonlyFromModifiers, this.props.record.evalContext) || false;
    }
}

export const colorField = {
    component: ColorField,
    supportedTypes: ["char"],
    extractProps: ({ modifiers }) => ({
        readonlyFromModifiers: modifiers.readonly,
    }),
};

registry.category("fields").add("color", colorField);
