/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useInputField } from "./input_field_hook";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class UrlField extends Component {
    setup() {
        useInputField(() => this.props.value || "");
    }

    get formattedHref() {
        let value = "";
        if (typeof this.props.value === "string") {
            const shouldaddPrefix = !(
                this.props.websitePath ||
                this.props.value.includes("://") ||
                /^\//.test(this.props.value)
            );
            value = shouldaddPrefix ? `http://${this.props.value}` : this.props.value;
        }
        return value;
    }
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}

UrlField.template = "web.UrlField";
UrlField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    text: { type: String, optional: true },
    websitePath: { type: Boolean, optional: true },
};
UrlField.displayName = _lt("URL");
UrlField.supportedTypes = ["char"];
UrlField.extractProps = (fieldName, record, attrs) => {
    return {
        text: attrs.text,
        websitePath: Boolean(attrs.options.website_path),
    };
};

registry.category("fields").add("url", UrlField);
