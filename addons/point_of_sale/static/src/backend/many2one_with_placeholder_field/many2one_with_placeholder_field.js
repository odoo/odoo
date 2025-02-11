import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

export class Many2OneFieldWithPlaceholderField extends Component {
    static template = "point_of_sale.Many2OneFieldWithPlaceholderField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            placeholder: this.props.record.data[this.props.placeholderField] || props.placeholder,
        };
    }
}

registry.category("fields").add("many2one_with_placeholder_field", {
    ...buildM2OFieldDescription(Many2OneFieldWithPlaceholderField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            placeholderField: staticInfo.options.placeholder_field,
        };
    },
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
        },
    ],
});
