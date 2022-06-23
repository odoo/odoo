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
}

ColorField.template = "web.ColorField";
ColorField.props = {
    ...standardFieldProps,
};
ColorField.extractProps = (fieldName, record) => {
    return {
        readonly: record.isReadonly(fieldName),
    };
};
ColorField.supportedTypes = ["char"];

registry.category("fields").add("color", ColorField);
