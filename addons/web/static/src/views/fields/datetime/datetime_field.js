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
 *  startDateField?: string;
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
        startDateField: { type: String, optional: true },
        warnFuture: { type: Boolean, optional: true },
    };

    static template = "web.DateTimeField";

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get endDateField() {
        return this.props.endDateField || this.props.name;
    }

    get relatedField() {
        return this.props.startDateField || this.props.endDateField;
    }

    get showRange() {
        return (
            this.relatedField &&
            ((this.props.required && !this.props.readonly) || this.values.some(Boolean))
        );
    }

    get startDateField() {
        return this.props.startDateField || this.props.name;
    }

    get values() {
        return ensureArray(this.state.value);
    }

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        const { name } = this.props; // should not change

        this.rootRef = useRef("root");
        this.inputRefs = [useRef("start-date"), useRef("end-date")];

        const dateTimePicker = useDateTimePicker({
            target: "root",
            pickerProps: (props) => this.getPickerProps(props),
            onChange: (value) => {
                if (Array.isArray(value)) {
                    if (value.every(Boolean)) {
                        this.emptyField = null;
                    } else {
                        this.emptyField = value[1] ? this.startDateField : this.endDateField;
                        if (!this.props.required) {
                            this.state.focusedDateIndex = 0;
                            this.state.value = value.find(Boolean);
                        }
                    }
                }
                this.triggerIsDirty(this.props);
            },
            onApply: (value) => {
                const toUpdate = {};
                if (Array.isArray(value)) {
                    // Value is already a range
                    [toUpdate[this.startDateField], toUpdate[this.endDateField]] = value;
                } else {
                    toUpdate[this.emptyField === name ? this.relatedField : name] = value;
                    if (this.relatedField && this.emptyField) {
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
        this.state = useState(dateTimePicker.state);
        this.openPicker = dateTimePicker.open;

        onWillStart(() => this.triggerIsDirty(this.props));
        onWillUpdateProps((nextProps) => this.triggerIsDirty(nextProps));
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    async addDate() {
        const nextFocusedIndex = this.emptyField === this.startDateField ? 0 : 1;
        const [value] = this.values;
        this.state.value = [value, value];
        this.emptyField = null;
        this.openPicker(nextFocusedIndex);
    }

    /**
     * @param {number} valueIndex
     */
    getFormattedValue(valueIndex) {
        const value = this.values[valueIndex];
        return value ? (this.type === "date" ? formatDate(value) : formatDateTime(value)) : "";
    }

    /**
     * @param {DateTimeFieldProps} props
     */
    getPickerProps(props) {
        const { record, name, maxDate, minDate, rounding } = props;
        const value = this.getValueFromProps(props);

        // Compute own props
        this.type = record.fields[name].type;
        if (this.relatedField) {
            this.emptyField =
                !Array.isArray(value) &&
                (record.data[this.relatedField] ? name : this.relatedField);
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
    getValueFromProps({ endDateField, name, record, required, startDateField }) {
        const value = record.data[name];
        const relatedField = startDateField || endDateField;
        if (relatedField) {
            const relatedValue = record.data[relatedField];
            if (required || (value && relatedValue)) {
                const range = [value, value];
                range[startDateField ? 0 : 1] = relatedValue;
                return range;
            } else if (!value) {
                return relatedValue;
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
        props.record.model.bus.trigger(
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

const START_DATE_FIELD_OPTION = "start_date_field";
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
        startDateField: options[START_DATE_FIELD_OPTION],
        warnFuture: archParseBoolean(options.warn_future),
    }),
    fieldDependencies: ({ type, modifiers, options }) => {
        const deps = [];
        if (options[START_DATE_FIELD_OPTION]) {
            deps.push({ name: options[START_DATE_FIELD_OPTION], type, modifiers });
            if (options[END_DATE_FIELD_OPTION]) {
                console.warn(
                    `A field cannot have both ${START_DATE_FIELD_OPTION} and ${END_DATE_FIELD_OPTION} options at the same time`
                );
            }
        } else if (options[END_DATE_FIELD_OPTION]) {
            deps.push({ name: options[END_DATE_FIELD_OPTION], type, modifiers });
        }
        return deps;
    },
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
            label: _lt("Start date field"),
            name: START_DATE_FIELD_OPTION,
            type: "field",
            availableTypes: ["date", "datetime"],
        },
        {
            label: _lt("End date field"),
            name: END_DATE_FIELD_OPTION,
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
