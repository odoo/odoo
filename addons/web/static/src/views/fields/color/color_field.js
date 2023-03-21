/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

export class ColorField extends Component {
    static template = "web.ColorField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({
            color: this.props.record.data[this.props.name] || "",
        });

        onWillUpdateProps((nextProps) => {
            this.state.color = nextProps.record.data[nextProps.name] || "";
        });
    }
}

export const colorField = {
    component: ColorField,
    supportedTypes: ["char"],
    extractProps(fieldInfo, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("color", colorField);
