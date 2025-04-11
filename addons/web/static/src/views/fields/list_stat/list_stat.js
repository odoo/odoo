
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ListStatField extends Component {
    static template = "web.ListStatField";
    static props = {
        ...standardFieldProps,
        iconClass: { type: String },
        label: { type: String },
    };
}

export const listStatField = {
    component: ListStatField,
    displayName: _t("List Stat"),
    supportedOptions: [
        {
            label: _t("Icon Class"),
            name: "icon_class",
            type: "string",
        },
        {
            label: _t("Label"),
            name: "label",
            type: "string",
        },
    ],
    supportedTypes: ["integer", "float"],
    extractProps: ({ options }) => ({
        iconClass: options.icon_class,
        label: options.label,

    }),
};

registry.category("fields").add("list_stat", listStatField);
