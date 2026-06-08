import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/** Toggle button for boolean values, with a custom label and custom classes for each state. */
export class BooleanToggleLabelField extends Component {
    static template = "mail.BooleanToggleLabelField";
    static props = {
        ...standardFieldProps,
        btnClassOn: { type: String },
        btnClassOff: { type: String },
        label: { type: String },
    };

    update() {
        this.props.record.update({ [this.props.name]: !this.props.record.data[this.props.name] });
    }
}

export const booleanToggleLabelField = {
    component: BooleanToggleLabelField,
    displayName: _t("Boolean Label"),
    supportedTypes: ["boolean"],
    extractProps: ({ string, options }, dynamicInfo) => ({
        btnClassOn: options.btn_class_on ?? "btn-primary",
        btnClassOff: options.btn_class_off ?? "btn-outline-primary",
        label: string,
        readonly: dynamicInfo.readonly,
    }),
};

registry.category("fields").add("mail_boolean_toggle_label", booleanToggleLabelField);
