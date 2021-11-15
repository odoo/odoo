/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class ColorField extends Component {
    onClick(ev) {
        // ...
    }
}
ColorField.template = "web.ColorField";

ColorField.props = {
    ...standardFieldProps,
};

registry.category("fields").add("color", ColorField);
