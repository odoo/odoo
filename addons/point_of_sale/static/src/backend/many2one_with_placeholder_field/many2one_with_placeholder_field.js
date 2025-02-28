import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { Component } from "@odoo/owl";

export class Many2OneFieldWithPlaceholderField extends Component {
    static template = "point_of_sale.Many2OneFieldWithPlaceholderField";
    static components = { Many2One };
    static props = {
        ...Many2OneField.props,
        placeholderField: { type: String, optional: true },
    };

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            placeholder:
                this.props.record.data[this.props.placeholderField] || this.props.placeholder,
        };
    }
}

registry.category("fields").add("many2one_with_placeholder_field", {
    ...buildM2OFieldDescription(Many2OneFieldWithPlaceholderField),
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
        },
    ],
    extractProps(params, dynamicInfo) {
        return {
            ...extractM2OFieldProps(params, dynamicInfo),
            placeholderField: params.options.placeholder_field,
        };
    },
});
