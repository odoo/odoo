import { Component } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ConversionError, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";

const { DateTime } = luxon;

export class BuilderDateTimePicker extends Component {
    static template = "html_builder.BuilderDateTimePicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        type: { type: [{ value: "date" }, { value: "datetime" }], optional: true },
        format: { type: String, optional: true },
    };
    static defaultProps = {
        type: "datetime",
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.getDefaultValue(),
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.state = state;
        this.oldValue = this.state.value;

        this.commit = (userInputValue) => {
            this.isPreviewing = false;
            const result = commit(userInputValue);
            if (result) {
                this.oldValue = parseDateTime(result).toUnixInteger().toString();
            }
            return result;
        };

        this.preview = (userInputValue) => {
            this.isPreviewing = true;
            preview(userInputValue);
        };

        const getPickerProps = () => ({
            type: this.props.type,
            minDate: DateTime.fromObject({ year: 1000 }),
            maxDate: DateTime.now().plus({ year: 200 }),
            value: this.getCurrentValueDateTime(),
            rounding: 0,
        });

        this.inputRef = useChildRef();

        this.dateTimePicker = useDateTimePicker({
            target: "root",
            format: this.props.format,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (value) => {
                const result = this.commit(formatDateTime(value));
                this.inputRef.el.value = result;
            },
            onChange: (value) => {
                const dateString = formatDateTime(value);
                this.preview(dateString);
                this.inputRef.el.value = dateString;
            },
        });
    }

    /**
     * @returns {String} number of seconds since epoch
     */
    getDefaultValue() {
        return DateTime.now().toUnixInteger().toString();
    }

    /**
     * @returns {DateTime} the current value of the datetime picker
     */
    getCurrentValueDateTime() {
        return DateTime.fromSeconds(parseInt(this.state.value));
    }

    /**
     * @param {String} rawValue - the raw value in seconds
     * @returns {String} a formatted date string
     */
    formatRawValue(rawValue) {
        return formatDateTime(DateTime.fromSeconds(parseInt(rawValue)));
    }

    /**
     * @param {String} displayValue - representing a date
     * @returns {String} number of seconds
     */
    parseDisplayValue(displayValue) {
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
                return this.oldValue;
            }
        }
        return this.getDefaultValue();
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
