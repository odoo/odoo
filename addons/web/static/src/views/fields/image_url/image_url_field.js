/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

export class ImageUrlField extends Component {
    static template = "web.ImageUrlField";
    static props = {
        ...standardFieldProps,
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
    };

    static fallbackSrc = "/web/static/img/placeholder.png";

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            src: this.props.value,
        });

        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.state.value = nextProps.value;
            }
        });
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
        this.state.src = this.constructor.fallbackSrc;
        this.notification.add(this.env._t("Could not display the specified image url."), {
            type: "info",
        });
    }
}

export const imageUrlField = {
    component: ImageUrlField,
    displayName: _lt("Image"),
    supportedTypes: ["char"],
    extractProps: ({ attrs }) => ({
        width: attrs.options.size ? attrs.options.size[0] : attrs.width,
        height: attrs.options.size ? attrs.options.size[1] : attrs.height,
    }),
};

registry.category("fields").add("image_url", imageUrlField);
// TODO WOWL: remove below when old registry is removed.
registry.category("fields").add("kanban.image_url", imageUrlField);
