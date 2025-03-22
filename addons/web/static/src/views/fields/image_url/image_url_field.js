/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";

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
            src: this.props.record.data[this.props.name],
        });

        useRecordObserver((record) => {
            this.state.src = record.data[this.props.name];
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
    }
}

export const imageUrlField = {
    component: ImageUrlField,
    displayName: _t("Image"),
    supportedOptions: [
        {
            label: _t("Size"),
            name: "size",
            type: "selection",
            choices: [
                { label: _t("Small"), value: "[0,90]" },
                { label: _t("Medium"), value: "[0,180]" },
                { label: _t("Large"), value: "[0,270]" },
            ],
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        width: options.size ? options.size[0] : attrs.width,
        height: options.size ? options.size[1] : attrs.height,
    }),
};

registry.category("fields").add("image_url", imageUrlField);
