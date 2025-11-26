/** @odoo-module **/

import { DateTimeField, dateField } from "@web/views/fields/datetime/datetime_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
/**
 * This extention introduces a new prop "minDateField" that works like "minDate" but allows the user to specify a field for a dynamic min value rather than a static value from a string
 *
 * @extends DateTimeField
 */
export class DynamicMinDateTimeField extends DateTimeField {
    static props = {
        ...DateTimeField.props,
        minDateField: { type: String, optional: true },
    };

    /**
     * @override
     * Extends the picker props to support a dynamically computed minimum date.
     *
     * Unlike the standard static `minDate` option (which accepts a literal string),
     * this enhancement allows the picker to derive its minimum date from another
     * date field via the `minDateField` prop. This makes it possible to enforce
     * contextual constraints.
     *  For example: ensuring that an end date cannot precede a start date, with the end_date DateTime picker automatically using the start_date as its minimum allowed value.
     * @returns {DateTimePickerProps} The picker configuration with the computed minDate.
     */

    getPickerProps() {
        const originalGetPickerProps = super.getPickerProps();
        if (this.props.minDateField) {
            const dynamicMinDateValue = this.props.record.data[this.props.minDateField];
            if (dynamicMinDateValue) {
                originalGetPickerProps.minDate = dynamicMinDateValue;
            }
        }
        return originalGetPickerProps;
    }
}

export const dynamicMinDateField = {
    ...dateField,
    component: DynamicMinDateTimeField,
    displayName: _t("Date with Dynamic Minimum Value"),
    supportedTypes: ["date", "datetime"],

    supportedOptions: [
        ...dateField.supportedOptions,
        {
            label: _t("Minimum Date Field"),
            name: "min_date_field",
            type: "field",
            availableTypes: ["date", "datetime"],
            help: _t("Reference another date/datetime field to use as minimum date"),
        },
    ],

    fieldDependencies: (args) => {
        const deps = dateField.fieldDependencies(args);
        if (args.options.min_date_field) {
            deps.push({
                name: args.options.min_date_field,
                type: "datetime",
                readonly: false,
            });
        }
        return deps;
    },

    extractProps: (fieldInfo, dynamicInfo) => {
        const baseProps = dateField.extractProps(fieldInfo, dynamicInfo);

        return {
            ...baseProps,
            minDateField: fieldInfo.options.min_date_field,
        };
    },
};

registry.category("fields").add("date_dynamic_min", dynamicMinDateField);
