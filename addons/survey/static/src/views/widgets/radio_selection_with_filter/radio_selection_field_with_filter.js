/** @odoo-module **/

import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class RadioSelectionFieldWithFilter extends RadioField {
    static props = {
        ...RadioField.props,
        allowed_selection: { type: Array },
    };

    get items() {
        return super.items.filter(([value, label]) => {
            return this.props.allowed_selection.includes(value);
        });
    }
}

export const radioSelectionFieldWithFilter = {
    ...radioField,
    component: RadioSelectionFieldWithFilter,
    displayName: _t("Radio for Selection With Filter"),
    supportedTypes: ["selection"],
    extractProps({ options }, { context: { allowed_selection } }) {
        return {
            ...radioField.extractProps(...arguments),
            allowed_selection: allowed_selection,
        };
    },
};

registry.category("fields").add("radio_selection_with_filter", radioSelectionFieldWithFilter);
