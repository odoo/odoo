/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};
const placeholder = "/web/static/img/placeholder.png";

export class ImageField extends Component {
    setup() {
        if (this.props.value) {
            const magic = fileTypeMagicWordMap[this.props.value[0] || "png"];
            this.url = `data:image/${magic};base64,${this.props.value}`;
        } else {
            this.url = placeholder;
        }
    }
}

ImageField.props = {
    ...standardFieldProps,
};
ImageField.template = "web.TextField";

registry.category("fields").add("image", ImageField);
