import { Component, proxy, signal, t, useEffect, useProps } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ConversionError, formatDate, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { textInputBasePassthroughProps } from "./builder_input_base";
import { BuilderTextInputBase } from "./builder_text_input_base";

const { DateTime } = luxon;

export class BuilderDateTimePicker extends Component {
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };
    static template = "html_builder.BuilderDateTimePicker";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        type: t.selection(["date", "datetime"]).optional("datetime"),
        format: t.string().optional(),
        acceptEmptyDate: t.boolean().optional(true),
        minDate: t.any().optional(() => DateTime.fromObject({ year: 1000 })),
        maxDate: t.any().optional(() => DateTime.now().plus({ year: 200 })),
        allowRelativeDate: t.boolean().optional(false),
    });
    textInputBaseProps = useProps(textInputBasePassthroughProps);

    rootRef = signal.ref();

    setup() {
        useBuilderComponent(this.props);
        this.defaultValue = DateTime.now().toUnixInteger().toString();
        this.previousValue = undefined;
        const { state, commit, preview } = useInputBuilderComponent(this.props, {
            defaultValue: this.props.acceptEmptyDate ? undefined : this.defaultValue,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.domState = state;
        this.state = proxy({});
        useEffect(() => {
            // State to display in the input.
            this.state.value = state.value;
        });

        this.commit = (userInputValue) => {
            this.isPreviewing = false;
            const result = commit(userInputValue);
            return result;
        };

        this.preview = (userInputValue) => {
            this.isPreviewing = true;
            preview(userInputValue);
        };

        const getPickerProps = () => ({
            type: this.props.type,
            minDate: this.props.minDate,
            maxDate: this.props.maxDate,
            value: this.getCurrentValueDateTime(),
            rounding: 1,
        });

        const isDateOnly = this.props.type === "date";
        this.formatDateTime = isDateOnly ? formatDate : formatDateTime;
        this.format = isDateOnly
            ? localization.dateFormat
            : localization.dateTimeFormat.replace(":ss", "").replace(".ss", "");

        this.dateTimePicker = useDateTimePicker({
            target: this.rootRef,
            format: this.props.format,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (value) => {
                this.commit(this.formatDateTime(value));
            },
            onChange: (value) => {
                const dateString = this.formatDateTime(value);
                this.preview(dateString);
                this.state.value = this.parseDisplayValue(dateString);
            },
        });
    }

    /**
     * @returns {DateTime} the current value of the datetime picker
     */
    getCurrentValueDateTime() {
        if (this.isToday) {
            return DateTime.now();
        }
        return this.domState.value ? DateTime.fromSeconds(parseInt(this.domState.value)) : false;
    }

    /**
     * @param {String} rawValue - the raw value in seconds
     * @returns {String} a formatted date string
     */
    formatRawValue(rawValue) {
        return rawValue
            ? this.formatDateTime(DateTime.fromSeconds(parseInt(rawValue)), { format: this.format })
            : "";
    }

    /**
     * @param {String} displayValue - representing a date
     * @returns {String} number of seconds
     */
    parseDisplayValue(displayValue) {
        if (displayValue === "today") {
            return displayValue;
        }
        if (displayValue === "" && this.props.acceptEmptyDate) {
            return undefined;
        }
        try {
            const parsedDateTime = parseDateTime(displayValue);
            if (parsedDateTime) {
                return parsedDateTime.set({ second: 0, millisecond: 0 }).toUnixInteger().toString();
            }
        } catch (e) {
            // A ConversionError means displayValue is an invalid date: fall
            // back to default value.
            if (!(e instanceof ConversionError)) {
                throw e;
            }
            if (!this.isPreviewing && displayValue !== "") {
                return this.domState.value;
            }
        }
        return this.defaultValue;
    }

    get isToday() {
        return this.state.value === "today";
    }

    /**
     * @returns {String} a formatted date string
     */
    get displayValue() {
        if (this.state.value === "today") {
            return _t("Today");
        }
        return this.state.value !== undefined ? this.formatRawValue(this.state.value) : undefined;
    }

    onFocus() {
        this.dateTimePicker.open();
    }

    toggleToday() {
        if (this.textInputBaseProps.disabled) {
            return;
        }
        if (!this.isToday) {
            this.previousValue = this.domState.value;
            this.dateTimePicker.close();
        }
        this.commit(this.isToday ? this.formatRawValue(this.previousValue) : "today");
    }
}
