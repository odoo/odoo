/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class ImageUrlField extends Component {
    get sizeStyle() {
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        return style;
    }
}

Object.assign(ImageUrlField, {
    template: "web.ImageUrlField",
    props: {
        ...standardFieldProps,
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
    },

    convertAttrsToProps(attrs) {
        return {
            width: attrs.options.size && attrs.options.size[0],
            height: attrs.options.size && attrs.options.size[1],
        };
    },
});

registry.category("fields").add("image_url", ImageUrlField);
