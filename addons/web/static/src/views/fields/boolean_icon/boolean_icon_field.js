import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

export class BooleanIconField extends Component {
    static template = "web.BooleanIconField";
    props = props({
        ...standardFieldProps,
        icon: t.string().optional("check_box"),
        label: t.string().optional(),
    });

    update() {
        this.props.record.update({ [this.props.name]: !this.props.record.data[this.props.name] });
    }
}

export const booleanIconField = {
    component: BooleanIconField,
    displayName: _t("Boolean Icon"),
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
        icon_class: options.icon_class,
        label: string,
    }),
};

registry.category("fields").add("boolean_icon", booleanIconField);
