import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MRPBooleanIconField extends Component {
    static template = "mrp.MRPBooleanIconField";
    static props = {
        ...standardFieldProps,
        icon: { type: String, optional: true },
        label: { type: String, optional: true },
    };
    static defaultProps = {
        icon: "fa-check-square-o",
    };
}

export const mrpBooleanIconField = {
    component: MRPBooleanIconField,
    displayName: _t("MRP Boolean Icon"),
    supportedOptions: [
        {
            label: _t("Icon"),
            name: "icon",
            type: "string",
        },
    ],
    supportedTypes: ["boolean"],
    extractProps: ({ options, string }) => ({
        icon: options.icon,
        label: string,
    }),
};

registry.category("fields").add("mrp_boolean_icon", mrpBooleanIconField);
