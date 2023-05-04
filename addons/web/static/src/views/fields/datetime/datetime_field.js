/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import {
    areDatesEqual,
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
    today,
} from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ensureArray } from "@web/core/utils/arrays";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

/**
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef {import("../standard_field_props").StandardFieldProps & {
 *  endDateField?: string;
 *  maxDate?: string;
 *  minDate?: string;
 *  placeholder?: string;
 *  required?: boolean;
 *  rounding?: number;
 *  warnFuture?: boolean;
 * }} DateTimeFieldProps
 *
 * @typedef {import("@web/core/datetime/datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

/** @extends {Component<DateTimeFieldProps>} */
export class DateTimeField extends Component {
    static props = {
        ...standardFieldProps,
        endDateField: { type: String, optional: true },
        maxDate: { type: String, optional: true },
        minDate: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        rounding: { type: Number, optional: true },
        warnFuture: { type: Boolean, optional: true },
    };

    static template = "web.DateTimeField";

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get hasEmptyField() {
        return this.values.length < 2 || !this.values.every(Boolean);
    }

    /** @type {string[]} */
    get refValues() {
        return this.inputRefs.map((ref) => ref.el?.value);
    }

    get showEndDateInput() {
        return this.props.endDateField && this.values.filter(Boolean).length;
    }

    get values() {
        return ensureArray(this.state.value);
    }

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        const { endDateField, name } = this.props; // should not change

        this.rootRef = useRef("root");
        this.inputRefs = [useRef("start-date"), useRef("end-date")];

        const state = useDateTimePicker({
            target: "root",
            pickerProps: (props) => this.getPickerProps(props),
            onChange: (value) => {
                if (Array.isArray(value)) {
                    if (value.every(Boolean)) {
                        this.emptyField = false;
                    } else {
                        this.emptyField = value[0] ? endDateField : name;
                        this.state.value = value.find(Boolean);
                    }
                }
                this.triggerIsDirty(this.props);
            },
            onApply: (value) => {
                const toUpdate = {};
                if (Array.isArray(value)) {
                    // Value is already a range
                    [toUpdate[name], toUpdate[endDateField]] = value;
                } else {
                    toUpdate[this.emptyField === name ? endDateField : name] = value;
                    if (endDateField && this.emptyField) {
                        toUpdate[this.emptyField] = false;
                    }
                }
                // Remove values that did not change
                for (const fieldName in toUpdate) {
                    if (areDatesEqual(toUpdate[fieldName], this.props.record.data[fieldName])) {
                        delete toUpdate[fieldName];
                    }
                }
                this.props.record.update(toUpdate);
            },
        });
        this.state = useState(state);

        onWillStart(() => this.triggerIsDirty(this.props));
        onWillUpdateProps((nextProps) => this.triggerIsDirty(nextProps));
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    async addDate() {
        const [value] = this.values;
        this.state.focusedDateIndex = this.emptyField === this.props.name ? 0 : 1;
        this.state.value = [value, value];
    }

    formatDisplayValue(value) {
        if (typeof value === "string") {
            return value;
        }
        return value ? (this.type === "date" ? formatDate(value) : formatDateTime(value)) : "";
    }

    /**
     * @param {DateTimeFieldProps} props
     */
    getPickerProps(props) {
        const { endDateField, record, name, maxDate, minDate, rounding } = props;
        const value = this.getValueFromProps(props);

        // Compute own props
        this.type = record.fields[name].type;
        if (endDateField) {
            this.emptyField =
                !Array.isArray(value) && (record.data[endDateField] ? name : endDateField);
        }

        // Compute picker props
        /** @type {DateTimePickerProps} */
        const pickerProps = { value, type: this.type };
        if (maxDate) {
            pickerProps.maxDate = maxDate === "today" ? maxDate : this.parseLimitDate(maxDate);
        }
        if (minDate) {
            pickerProps.minDate = minDate === "today" ? minDate : this.parseLimitDate(minDate);
        }
        if (!isNaN(rounding)) {
            pickerProps.rounding = rounding;
        }
        return pickerProps;
    }

    /**
     * @param {DateTimeFieldProps} props
     * @returns {DateTimePickerProps["value"]}
     */
    getValueFromProps({ endDateField, record, required, name }) {
        const value = record.data[name];
        if (endDateField) {
            const endValue = record.data[endDateField];
            if (required || (value && endValue)) {
                return [value, endValue];
            } else if (!value) {
                return endValue;
            }
        }
        return value;
    }

    /**
     * @param {number} index
     */
    isDateInTheFuture(index) {
        return this.values[index] > today();
    }

    /**
     * @param {string} value
     */
    parseLimitDate(value) {
        return this.type === "date" ? deserializeDate(value) : deserializeDateTime(value);
    }

    /**
     * The given props are used to compute the current value and compare it to
     * the state handled by the datetime hook.
     *
     * @param {DateTimeFieldProps} props
     */
    triggerIsDirty(props) {
        this.props.record.model.bus.trigger(
            "FIELD_IS_DIRTY",
            !areDatesEqual(this.getValueFromProps(props), this.state.value)
        );
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    onInput() {
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
    }
}

const END_DATE_FIELD_OPTION = "end_date_field";

export const dateField = {
    component: DateTimeField,
    displayName: _lt("Date"),
    supportedOptions: [
        {
            label: _lt("Earliest accepted date"),
            name: "min_date",
            type: "string",
            help: _lt(`ISO-formatted date (e.g. "2018-12-31") or "today".`),
        },
        {
            label: _lt("Latest accepted date"),
            name: "max_date",
            type: "string",
            help: _lt(`ISO-formatted date (e.g. "2018-12-31") or "today".`),
        },
        {
            label: _lt("Warning for future dates"),
            name: "warn_future",
            type: "boolean",
            help: _lt(`Displays a warning icon if the input dates are in the future.`),
        },
    ],
    supportedTypes: ["date"],
    extractProps: ({ attrs, modifiers, options }) => ({
        endDateField: options[END_DATE_FIELD_OPTION],
        maxDate: options.max_date,
        minDate: options.min_date,
        placeholder: attrs.placeholder,
        required: Boolean(modifiers.required),
        rounding: parseInt(options.rounding),
        warnFuture: archParseBoolean(options.warn_future),
    }),
    fieldDependencies: ({ type, modifiers, options }) =>
        options[END_DATE_FIELD_OPTION] && [
            { name: options[END_DATE_FIELD_OPTION], type, modifiers },
        ],
};

export const dateTimeField = {
    ...dateField,
    displayName: _lt("Date & Time"),
    supportedOptions: [
        ...dateField.supportedOptions,
        {
            label: _lt("Rounding"),
            name: "rounding",
            type: "number",
            default: 5,
            help: _lt(`Increment used in the minutes selection dropdown.`),
        },
    ],
    supportedTypes: ["datetime"],
};

export const dateRangeField = {
    ...dateTimeField,
    displayName: _lt("Date Range"),
    supportedOptions: [
        ...dateTimeField.supportedOptions,
        {
            label: _lt("End date field"),
            name: "end_date_field",
            type: "field",
            availableTypes: ["date", "datetime"],
        },
    ],
    supportedTypes: ["date", "datetime"],
};

registry
    .category("fields")
    .add("date", dateField)
    .add("daterange", dateRangeField)
    .add("datetime", dateTimeField);
