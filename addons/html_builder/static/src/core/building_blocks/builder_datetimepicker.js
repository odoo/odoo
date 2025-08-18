import { Component, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { effect } from "@web/core/utils/reactive";
import { ConversionError, formatDate, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { pick } from "@web/core/utils/objects";
import { BuilderComponent } from "./builder_component";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "../utils";

const { DateTime } = luxon;

export class BuilderDateTimePicker extends Component {
    static template = "html_builder.BuilderDateTimePicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        type: { type: [{ value: "date" }, { value: "datetime" }], optional: true },
        format: { type: String, optional: true },
        acceptEmptyDate: { type: Boolean, optional: true },
    };
    static defaultProps = {
        type: "datetime",
        acceptEmptyDate: true,
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        this.defaultValue = DateTime.now().toUnixInteger().toString();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.acceptEmptyDate ? undefined : this.defaultValue,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.domState = state;
        this.state = useState({});
        effect(
            ({ value }) => {
                // State to display in the input.
                this.state.value = value;
            },
            [state]
        );

        this.commit = (userInputValue) => {
            this.isPreviewing = false;
            const result = commit(userInputValue);
            return result;
        };

        this.preview = (userInputValue) => {
            this.isPreviewing = true;
            preview(userInputValue);
        };

        const minDate = DateTime.fromObject({ year: 1000 });
        const maxDate = DateTime.now().plus({ year: 200 });
        const getPickerProps = () => ({
            type: this.props.type,
            minDate,
            maxDate,
            value: this.getCurrentValueDateTime(),
            rounding: 0,
        });

        this.formatDateTime = this.props.type === "date" ? formatDate : formatDateTime;

        this.dateTimePicker = useDateTimePicker({
            target: "root",
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
        return this.domState.value ? DateTime.fromSeconds(parseInt(this.domState.value)) : false;
    }

    /**
     * @param {String} rawValue - the raw value in seconds
     * @returns {String} a formatted date string
     */
    formatRawValue(rawValue) {
        return rawValue ? this.formatDateTime(DateTime.fromSeconds(parseInt(rawValue))) : "";
    }

    /**
     * @param {String} displayValue - representing a date
     * @returns {String} number of seconds
     */
    parseDisplayValue(displayValue) {
        if (displayValue === "" && this.props.acceptEmptyDate) {
            return undefined;
        }
        try {
            const parsedDateTime = parseDateTime(displayValue);
            if (parsedDateTime) {
                return parsedDateTime.toUnixInteger().toString();
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

    /**
     * @returns {String} a formatted date string
     */
    get displayValue() {
        return this.state.value !== undefined ? this.formatRawValue(this.state.value) : undefined;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    onFocus() {
        this.dateTimePicker.open();
    }
}
