/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class ImageUrlField extends Component {
    setup() {
        this.notification = useService("notification");
    }

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

    onLoadFailed() {
        this.notification.add(this.env._t("Could not display the selected pdf"), {
            type: "danger",
        });
    }
}

ImageUrlField.template = "web.ImageUrlField";
ImageUrlField.props = {
    ...standardFieldProps,
    width: { type: Number, optional: true },
    height: { type: Number, optional: true },
};
ImageUrlField.displayName = _lt("Image");
ImageUrlField.supportedTypes = ["char"];
ImageUrlField.extractProps = (fieldName, record, attrs) => {
    return {
        width: attrs.options.size && attrs.options.size[0],
        height: attrs.options.size && attrs.options.size[1],
    };
};

registry.category("fields").add("image_url", ImageUrlField);
