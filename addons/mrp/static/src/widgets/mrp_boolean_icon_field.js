import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MRPBooleanIconField extends Component {
    static template = "mrp.MRPBooleanIconField";
    props = props({
        ...standardFieldProps,
        icon: t.string().optional("fa-check-square-o"),
        label: t.string().optional(),
    });
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
