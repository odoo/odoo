import { props, t } from "@odoo/owl";
import { RadioField, radioField, radioFieldProps } from "@web/views/fields/radio/radio_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class RadioSelectionFieldWithFilter extends RadioField {
    props = props({
        ...radioFieldProps,
        allowedSelectionField: t.string(),
    });

    get items() {
        const allowedItems = this.props.record.data[this.props.allowedSelectionField];
        return super.items.filter(([value]) => allowedItems.includes(value));
    }
}

export const radioSelectionFieldWithFilter = {
    ...radioField,
    component: RadioSelectionFieldWithFilter,
    displayName: _t("Radio for Selection With Filter"),
    supportedTypes: ["selection"],
    extractProps({ options }) {
        return {
            ...radioField.extractProps(...arguments),
            allowedSelectionField: options.allowed_selection_field,
        };
    },
};

registry.category("fields").add("radio_selection_with_filter", radioSelectionFieldWithFilter);
