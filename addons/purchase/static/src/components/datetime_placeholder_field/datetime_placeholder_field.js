import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DateTimeField, dateTimeField } from '@web/views/fields/datetime/datetime_field';

export class DatetimePlaceholderField extends DateTimeField {
    static template = "purchase.DatetimePlaceholderField";
    static props = {
        ...DateTimeField.props,
        placeholderField: { type: String, optional: true },
    };

    get placeholder() {
        return this.props.record.data[this.props.placeholderField] || this.props.placeholder;
    }

}

export const datetimePlaceholderField = {
    ...dateTimeField,
    component: DatetimePlaceholderField,
    supportedOptions: [
        ...dateTimeField.supportedOptions,
        {
            label: _t("Placeholder field"),
            name: "placeholder_field",
            type: "field",
        },
    ],
    extractProps(params, dynamicInfo) {
        return {
            ...dateTimeField.extractProps(params, dynamicInfo),
            placeholderField: params.options.placeholder_field,
        };
    },
};

registry.category("fields").add("datetime_placeholder_field", datetimePlaceholderField);
