/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

const { Component, useState } = owl;

export class ColorField extends Component {
    setup() {
        this.state = useState({
            color: this.props.value || "#000000",
        });
    }

    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
}

ColorField.template = "web.ColorField";
ColorField.props = {
    ...standardFieldProps,
};

ColorField.supportedTypes = ["char"];

registry.category("fields").add("color", ColorField);
