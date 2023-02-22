/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class UrlField extends Component {
    static template = "web.UrlField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        text: { type: String, optional: true },
        websitePath: { type: Boolean, optional: true },
    };

    setup() {
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "" });
    }

    get formattedHref() {
        let value = "";
        if (typeof this.props.record.data[this.props.name] === "string") {
            const shouldaddPrefix = !(
                this.props.websitePath ||
                this.props.record.data[this.props.name].includes("://") ||
                /^\//.test(this.props.record.data[this.props.name])
            );
            value = shouldaddPrefix
                ? `http://${this.props.record.data[this.props.name]}`
                : this.props.record.data[this.props.name];
        }
        return value;
    }
}

export const urlField = {
    component: UrlField,
    displayName: _lt("URL"),
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        text: attrs.text,
        websitePath: options.website_path,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("url", urlField);

class FormUrlField extends UrlField {
    static template = "web.FormUrlField";
}

export const formUrlField = {
    ...urlField,
    component: FormUrlField,
};

registry.category("fields").add("form.url", formUrlField);
