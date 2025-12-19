import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { InputBox } from "@web/core/input_box/input_box";
import { useChildRef } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class UrlField extends Component {
    static template = "web.UrlField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        text: { type: String, optional: true },
        websitePath: { type: Boolean, optional: true },
    };
    static components = { InputBox };

    setup() {
        this.input = useChildRef();
        useInputField({ ref: this.input, getValue: () => this.value });
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get formattedHref() {
        let value = this.props.record.data[this.props.name];
        if (value && !this.props.websitePath) {
            const regex = /^((ftp|http)s?:\/)?\//i; // http(s)://... ftp(s)://... /...
            value = !regex.test(value) ? `http://${value}` : value;
        }
        return value;
    }
}

export const urlField = {
    component: UrlField,
    displayName: _t("URL"),
    supportedOptions: [
        {
            label: _t("Is a website path"),
            name: "website_path",
            type: "boolean",
            help: _t("If True, the url will be used as it is, without any prefix added to it."),
        },
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ attrs, options, placeholder }) => ({
        placeholder,
        text: attrs.text,
        websitePath: options.website_path,
    }),
};

registry.category("fields").add("url", urlField);

class FormUrlField extends UrlField {
    get overlayButtons() {
        return [
            {
                icon: "fa-globe",
                href: this.formattedHref,
                name: _t("Go to URL")
            }
        ]
    }
}

export const formUrlField = {
    ...urlField,
    component: FormUrlField,
};

registry.category("fields").add("form.url", formUrlField);
