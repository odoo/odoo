import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { _t } from "@web/core/l10n/translation";

export class Many2OneFieldWithPlaceholderField extends Many2OneField {
    static props = {
        ...Many2OneField.props,
        placeholderField: { type: String, optional: true },
    };

    get Many2XAutocompleteProps() {
        return {
            ...super.Many2XAutocompleteProps,
            placeholder:
                this.props.record.data[this.props.placeholderField] || this.props.placeholder,
        };
    }
}

export const many2OneFieldWithPlaceholderField = {
    ...many2OneField,
    component: Many2OneFieldWithPlaceholderField,
    supportedOptions: [
        ...many2OneField.supportedOptions,
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
        },
    ],
    extractProps(params, dynamicInfo) {
        return {
            ...many2OneField.extractProps(params, dynamicInfo),
            placeholderField: params.options.placeholder_field,
        };
    },
};

registry
    .category("fields")
    .add("many2one_with_placeholder_field", many2OneFieldWithPlaceholderField);
